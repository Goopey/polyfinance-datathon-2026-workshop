"""P4 — Les Lambda enchaînées par la vraie machine d'états donnent le même résultat que le pipeline local.

Conception : docs/06_AWS.md, infra/statemachine/pipeline.asl.json
Aucun appel AWS : S3 et DynamoDB sont remplacés par leurs équivalents locaux (`aws_runtime`), la
machine d'états est interprétée par `asl_runner`, les agents sont simulés.
"""
import json

import pytest

from easytrade.agents.llm_client import LLMOutputError, LLMUnavailableError
from easytrade.agents.simulated import simulated_client
from easytrade.orchestration import aws_runtime
from easytrade.orchestration.handlers import (
    debate,
    decision,
    evidence_packs,
    explanation,
    failure,
    profile,
    research,
    validation,
)
from easytrade.orchestration.handlers.common import RESULT
from easytrade.orchestration.pipeline import make_run_id
from tests.aws.asl_runner import AslRunner, ExecutionFailed
from tests.conftest import REPO_ROOT

ASL = json.loads((REPO_ROOT / "infra" / "statemachine" / "pipeline.asl.json").read_text(encoding="utf-8"))
RESOURCES = {
    "Profile": profile.handler, "Validation": validation.handler, "Research": research.handler,
    "EvidencePacks": evidence_packs.handler, "Debate": debate.handler, "Decision": decision.handler,
    "Explanation": explanation.handler, "Failure": failure.handler,
}


class FlakyClient:
    """Client simulé dont certains appels échouent (étape choisie par `fails`)."""

    def __init__(self, fails, error):
        self.inner, self.fails, self.error, self.calls = simulated_client(), fails, error, []

    def model_id(self, tier):
        return self.inner.model_id(tier)

    def invoke(self, **kwargs):
        self.calls.append(kwargs["step"])
        if self.fails(kwargs["step"]):
            raise self.error
        return self.inner.invoke(**kwargs)


@pytest.fixture
def aws_env(tmp_path, monkeypatch, workspace):
    """Stockage local à la place de S3 / DynamoDB ; données et client partagés comme dans un conteneur."""
    monkeypatch.setenv("EASYTRADE_STATE_DIR", str(tmp_path / "s3"))
    monkeypatch.setenv("EASYTRADE_TABLE_DIR", str(tmp_path / "dynamodb"))
    monkeypatch.setattr(aws_runtime, "workspace", lambda: workspace)
    client = {"value": simulated_client()}
    monkeypatch.setattr(aws_runtime, "llm", lambda: client["value"])

    def use_client(value):
        client["value"] = value

    return use_client


def execution_input(workspace, profile_id, ticker=None, persona=None):
    as_of = workspace.settings.as_of
    aws_runtime.run_table().put_run({"run_id": make_run_id(as_of, profile_id, ticker), "profile_id": profile_id,
                                     "as_of": str(as_of), "requested_ticker": ticker, "status": "en_cours",
                                     "steps": "[]", "error": None})
    return {"run_id": make_run_id(as_of, profile_id, ticker), "profile_id": profile_id, "as_of": str(as_of),
            "requested_ticker": ticker, "persona": persona, "profile_source": None}


def run_machine(payload):
    runner = AslRunner(ASL, RESOURCES)
    return runner, runner.run(payload)


@pytest.mark.parametrize("profile_id,ticker", [("amira", None), ("robert", "TSLA"), ("mateo", None)])
def test_machine_identique_au_pipeline_local(aws_env, workspace, pipeline_run, profile_id, ticker):
    payload = execution_input(workspace, profile_id, ticker)
    runner, output = run_machine(payload)
    local = pipeline_run(profile_id, ticker)
    remote = aws_runtime.state_store().load(payload["run_id"], RESULT)

    assert output["status"] == "termine" == local.status
    assert "MarquerEchec" not in runner.visited
    # Même analyse : mêmes preuves (identifiants compris), même décision, même explication.
    assert remote.ledger.ids() == local.ledger.ids()
    assert remote.decision.model_dump() == local.decision.model_dump()
    assert remote.explanation.model_dump() == local.explanation.model_dump()
    assert [s.step for s in remote.trace.steps] == [s.step for s in local.trace.steps]
    # Le débat passe par l'état Map : une invocation par candidat.
    assert runner.visited.count("DebatDUnCandidat") == len(local.debate)
    item = aws_runtime.run_table().get_run(payload["run_id"])
    assert item["status"] == "termine" and item["error"] is None
    assert len(aws_runtime.steps_from_payload(item["steps"])) == len(local.trace.steps)


def test_artefacts_json_du_run(aws_env, workspace, tmp_path):
    payload = execution_input(workspace, "amira")
    run_machine(payload)
    folder = tmp_path / "s3" / "runs" / payload["run_id"]
    for name in ("run.json", "trace.json", "evidence.json", "explanation.json", "decision.json"):
        assert (folder / name).exists(), name
    assert json.loads((folder / "run.json").read_text(encoding="utf-8"))["status"] == "termine"


def test_bedrock_indisponible_relances_puis_echec_visible(aws_env, workspace):
    client = FlakyClient(lambda step: step == "research", LLMUnavailableError("quota Bedrock atteint"))
    aws_env(client)
    payload = execution_input(workspace, "amira")
    runner = AslRunner(ASL, RESOURCES)
    with pytest.raises(ExecutionFailed) as failed:
        runner.run(payload)

    assert failed.value.error == "AnalyseEchouee"
    assert client.calls.count("research") == 3  # premier essai + 2 relances (Retry de l'état Recherche)
    assert runner.visited[-2:] == ["MarquerEchec", "AnalyseEchouee"]
    item = aws_runtime.run_table().get_run(payload["run_id"])
    assert item["status"] == "echec" and "quota Bedrock atteint" in item["error"]
    result = aws_runtime.state_store().load(payload["run_id"], RESULT)
    failed_steps = [s for s in result.trace.steps if s.status == "echec"]
    assert [s.step for s in failed_steps] == ["recherche"]
    assert [s.step for s in result.trace.steps if s.status == "ok"][:2] == ["profil", "validation"]


def test_sortie_invalide_echec_sans_relance(aws_env, workspace):
    client = FlakyClient(lambda step: step.startswith("debate."), LLMOutputError("sortie non conforme"))
    aws_env(client)
    payload = execution_input(workspace, "amira")
    runner = AslRunner(ASL, RESOURCES)
    with pytest.raises(ExecutionFailed):
        runner.run(payload)

    assert runner.visited.count("DebatDUnCandidat") == 1  # pas de relance : erreur définitive
    item = aws_runtime.run_table().get_run(payload["run_id"])
    assert item["status"] == "echec" and "LLMOutputError" in item["error"]
    result = aws_runtime.state_store().load(payload["run_id"], RESULT)
    assert any(s.step == "debat" and s.status == "echec" for s in result.trace.steps)


def test_titre_inconnu_echec_avant_tout_enregistrement(aws_env, workspace):
    payload = execution_input(workspace, "robert", "ZZZZ")
    with pytest.raises(ExecutionFailed):
        run_machine(payload)
    item = aws_runtime.run_table().get_run(payload["run_id"])
    assert item["status"] == "echec" and "ZZZZ" in item["error"]
