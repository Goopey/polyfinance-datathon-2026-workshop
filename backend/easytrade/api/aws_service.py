"""Service de l'API sur AWS : runs dans DynamoDB, exécution par Step Functions, résultats sur S3.

Conception : docs/06_AWS.md, api/service.py
Seuls le stockage et le lancement changent par rapport à `ApiService` : les routes, les contrats du
mobile et la traduction des résultats sont les mêmes. Une Lambda API peut être servie par plusieurs
conteneurs : rien d'utile n'est gardé seulement en mémoire.
- `POST /runs` inscrit le run (« en_cours ») puis démarre une exécution de la machine d'états.
- `GET /runs/{id}` lit la progression dans DynamoDB (écrite par chaque étape) ; à la fin, le résultat
  complet (`RunResult` : explication, registre de preuves, indicateurs) est lu sur S3.
- Les profils fictifs créés par questionnaire sont enregistrés dans la table et transmis à l'exécution.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

from easytrade.agents.llm_client import LLMClient
from easytrade.api.service import ApiService, NotFound, RunEntry
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.orchestration import aws_runtime
from easytrade.orchestration.handlers.common import RESULT
from easytrade.orchestration.pipeline import RunResult, Workspace
from easytrade.schemas.api import ProfileDraft, ProfileWeightsView, RunRequest
from easytrade.schemas.trace import RunTrace

# Un run « en_cours » sans nouvelle depuis ce délai est considéré comme perdu et peut être relancé.
STALE_AFTER = timedelta(minutes=20)

Launcher = Callable[[str, dict], Any]


class StepFunctionsLauncher:
    """Démarre une exécution de la machine d'états (nom unique : le même run peut être relancé)."""

    def __init__(self, state_machine_arn: str, client: Any = None):
        self.arn, self._client = state_machine_arn, client

    def __call__(self, run_id: str, payload: dict) -> str:
        if self._client is None:
            import boto3

            self._client = boto3.client("stepfunctions", region_name=os.environ.get("AWS_REGION"))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        name = re.sub(r"[^A-Za-z0-9_-]", "_", run_id)[:55] + "-" + stamp  # ≤ 80 caractères, unique
        response = self._client.start_execution(
            stateMachineArn=self.arn, name=name, input=json.dumps(payload, ensure_ascii=False, default=str))
        return response["executionArn"]


def _stale(item: dict) -> bool:
    try:
        updated = datetime.fromisoformat(item.get("updated_at") or "")
    except ValueError:
        return True
    return datetime.now(timezone.utc) - updated > STALE_AFTER


class AwsApiService(ApiService):
    def __init__(self, workspace: Optional[Workspace] = None, client: Optional[LLMClient] = None, *,
                 table: Optional[aws_runtime.RunTable] = None, store: Optional[aws_runtime.StateStore] = None,
                 launcher: Optional[Launcher] = None):
        super().__init__(workspace=workspace or aws_runtime.workspace(), client=client or aws_runtime.llm(),
                         max_workers=1)
        self.table = table or aws_runtime.run_table()
        self.store = store or aws_runtime.state_store()
        self.launch = launcher or StepFunctionsLauncher(os.environ["EASYTRADE_STATE_MACHINE_ARN"])
        self._base_ids = {entry["id"] for entry in self._base_personas}
        self._results: dict[tuple[str, str], RunResult] = {}

    # --- profils fictifs : enregistrés dans la table ---------------------------------------------
    def _entry(self, profile_id: str) -> dict:
        try:
            return super()._entry(profile_id)
        except NotFound:
            entry = self.table.get_profile(profile_id)
            if entry is None:
                raise
            with self._lock:
                if not any(e["id"] == profile_id for e in self._personas["personas"]):
                    self._personas["personas"].append(entry)
            return entry

    def create_profile(self, draft: ProfileDraft) -> ProfileWeightsView:
        view = super().create_profile(draft)
        self.table.put_profile(self._entry(view.profile_id))
        return view

    # --- runs : DynamoDB + Step Functions + S3 ---------------------------------------------------
    def start_run(self, request: RunRequest) -> str:
        entry, ticker, as_of, run_id = self._prepare_run(request)
        existing = self.table.get_run(run_id)
        # Le pipeline est déterministe : un run identique en cours ou terminé est réutilisé.
        if existing is not None and (existing.get("status") == "termine"
                                     or (existing.get("status") == "en_cours" and not _stale(existing))):
            return run_id
        self.table.put_run({"run_id": run_id, "profile_id": request.profile_id, "as_of": str(as_of),
                            "requested_ticker": ticker, "status": "en_cours", "steps": "[]", "error": None})
        payload = {
            "run_id": run_id, "profile_id": request.profile_id, "as_of": str(as_of), "requested_ticker": ticker,
            "persona": None if entry["id"] in self._base_ids else entry,
            "profile_source": self._profile_source(entry),
        }
        try:
            self.launch(run_id, payload)
        except Exception as error:
            self.table.update_run(run_id, status="echec", error=f"Lancement de l'analyse impossible : {error}")
            raise
        return run_id

    def _result(self, item: dict) -> RunResult:
        run_id = item["run_id"]
        key = (run_id, item.get("updated_at") or "")
        with self._lock:
            cached = self._results.get(key)
        if cached is not None:
            return cached
        if self.store.exists(run_id, RESULT):
            result = self.store.load(run_id, RESULT)
        else:  # échec avant tout enregistrement (ex. lancement refusé) : résultat minimal, erreur visible
            as_of = date.fromisoformat(item["as_of"])
            result = RunResult(
                run_id=run_id, status=item.get("status") or "echec", as_of=as_of, profile_id=item["profile_id"],
                requested_ticker=item.get("requested_ticker"), model_id=self.client.model_id("strong"),
                trace=RunTrace(run_id=run_id, as_of=as_of, profile_id=item["profile_id"],
                               steps=tuple(aws_runtime.steps_from_payload(item.get("steps")))),
                ledger=EvidenceLedger(as_of), error=item.get("error"),
            )
        with self._lock:
            self._results[key] = result
        return result

    def _run(self, run_id: str) -> RunEntry:
        item = self.table.get_run(run_id)
        if item is None:
            raise NotFound(f"Analyse inconnue : {run_id}")
        run = RunEntry(run_id=run_id, profile_id=item["profile_id"], as_of=date.fromisoformat(item["as_of"]),
                       requested_ticker=item.get("requested_ticker"),
                       steps=aws_runtime.steps_from_payload(item.get("steps")))
        if item.get("status") in aws_runtime.FINAL_STATUSES:
            run.result = self._result(item)
        return run
