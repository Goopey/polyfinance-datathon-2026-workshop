"""Lambda : marque un run en échec quand une étape s'arrête sans l'avoir fait (chemin `Catch`).

Conception : docs/06_AWS.md, infra/statemachine/pipeline.asl.json
Cas couverts : relances épuisées (Bedrock indisponible), délai dépassé, mémoire insuffisante. Si
l'étape a déjà marqué le run (« StageError »), rien n'est refait. L'étape en cause est lue dans le
message d'erreur (« [étape] … ») et inscrite dans la trace : l'échec reste visible, jamais masqué.
Entrée : `{"run_id", "error": {"Error", "Cause"}}`.
"""
from __future__ import annotations

import json
import re
from typing import Any

from easytrade.orchestration import aws_runtime
from easytrade.orchestration.handlers.common import CONTEXT, finalize, load_context
from easytrade.orchestration.pipeline import fail, record_debate_failure

STAGE_KINDS = {"profil": "llm", "validation": "code", "recherche": "llm", "dossiers_de_preuves": "code",
               "debat": "llm", "decision": "code", "explication": "llm"}


def _message(error: dict) -> str:
    cause = error.get("Cause") or ""
    try:
        cause = json.loads(cause).get("errorMessage", cause)
    except (ValueError, AttributeError):
        pass
    return f"{error.get('Error', 'Erreur')} : {cause}".strip(" :")


def handler(event: dict, context: Any = None) -> dict:
    run_id = event["run_id"]
    table = aws_runtime.run_table()
    item = table.get_run(run_id) or {}
    if item.get("status") in aws_runtime.FINAL_STATUSES:
        return {"run_id": run_id, "status": item["status"]}  # déjà marqué par l'étape elle-même
    message = _message(event.get("error") or {})
    if not aws_runtime.state_store().exists(run_id, CONTEXT):  # échec avant le premier enregistrement
        table.update_run(run_id, status="echec", error=message)
        return {"run_id": run_id, "status": "echec"}
    ctx = load_context(run_id)
    found = re.search(r"\[([a-z_]+)\]", message)
    stage = found.group(1) if found else "pipeline"
    if stage == "debat":
        record_debate_failure(ctx, message)
    else:
        ctx.trace.record(stage, STAGE_KINDS.get(stage, "code"), "echec", note=message)
    fail(ctx, message)
    finalize(ctx)
    return {"run_id": run_id, "status": "echec"}
