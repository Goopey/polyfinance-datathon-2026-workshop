"""Précalcul : débat parallèle identique au débat en série, vues de profil gardées, script de précalcul.

Conception : scripts/precompute.py, docs/06_AWS.md (section « Précalcul »)
"""
import importlib.util
import time

import pytest

from easytrade.agents.simulated import simulated_client
from easytrade.api.aws_service import AwsApiService
from easytrade.orchestration import aws_runtime
from easytrade.orchestration.pipeline import run_pipeline
from tests.aws.test_aws_api import Launcher
from tests.aws.test_state_machine import aws_env  # noqa: F401  (fixture)
from tests.conftest import REPO_ROOT


def _load_precompute():
    spec = importlib.util.spec_from_file_location("precompute", REPO_ROOT / "scripts" / "precompute.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("profile_id,ticker", [("amira", None), ("robert", "TSLA")])
def test_debat_parallele_identique_au_debat_en_serie(workspace, pipeline_run, profile_id, ticker):
    parallel = run_pipeline(profile_id, requested_ticker=ticker, client=simulated_client(), workspace=workspace,
                            max_workers=3, candidate_workers=4)
    serial = pipeline_run(profile_id, ticker)
    assert parallel.ledger.ids() == serial.ledger.ids()
    assert parallel.decision.model_dump() == serial.decision.model_dump()
    assert parallel.explanation.model_dump() == serial.explanation.model_dump()
    assert list(parallel.debate) == list(serial.debate)  # ordre des dossiers conservé


class NoModel:
    """Client qui refuse tout appel : prouve qu'une vue gardée ne rappelle pas le modèle."""

    def model_id(self, tier):
        return "us.anthropic.test"

    def invoke(self, **kwargs):
        raise AssertionError(f"appel au modèle inattendu : {kwargs['step']}")


def test_vue_de_profil_calculee_une_fois_puis_lue_dans_la_table(aws_env, workspace):  # noqa: F811
    def make(client):
        return AwsApiService(workspace=workspace, client=client, table=aws_runtime.run_table(),
                             store=aws_runtime.state_store(), launcher=Launcher())

    first = make(simulated_client()).profile_view("robert")
    again = make(NoModel()).profile_view("robert")  # autre conteneur, aucun appel au modèle
    assert again == first


def test_script_de_precalcul_sur_l_api(workspace):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from easytrade.api.app import create_app
    from easytrade.api.service import ApiService

    service = ApiService(workspace=workspace, client=simulated_client())
    api = TestClient(create_app(service))

    def request(method, path, body=None):
        response = api.request(method, path, json=body)
        assert response.status_code == 200, response.text
        return response.json()

    precompute = _load_precompute()
    logs = []
    results = precompute.precompute(request, tickers="TSLA,BTC-USD", concurrency=3, poll=0.05,
                                    log=logs.append, sleep=time.sleep)

    assert len(results) == 3 + 3 * 2
    assert {r["status"] for r in results} == {"termine"}
    assert any("profil robert : prêt" in line for line in logs)
    # Une seconde passe ne relance rien : chaque demande trouve son run terminé.
    launched = len(service._runs)
    again = precompute.precompute(request, tickers="TSLA,BTC-USD", concurrency=3, poll=0.05, log=lambda _: None)
    assert len(service._runs) == launched and {r["status"] for r in again} == {"termine"}
