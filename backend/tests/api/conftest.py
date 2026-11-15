"""Fixtures des tests d'API : application sur les vraies données, agents simulés, schéma du contrat mobile."""
import json
import time

import pytest

from tests.conftest import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "mobile" / "contracts.schema.json"


@pytest.fixture(scope="session")
def contract():
    """Validateur du contrat mobile : `contract("RunStatus", payload)` lève si le JSON n'est pas conforme.

    Le schéma est généré depuis mobile/src/types/contracts.ts (`npm run contracts` dans mobile/).
    """
    jsonschema = pytest.importorskip("jsonschema")
    if not SCHEMA_PATH.exists():
        pytest.skip("mobile/contracts.schema.json absent : lancer `npm run contracts` dans mobile/")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validators = {}

    def check(type_name: str, payload, label: str = "") -> None:
        assert type_name in schema["definitions"], f"type absent du contrat mobile : {type_name}"
        if type_name not in validators:
            validators[type_name] = jsonschema.Draft7Validator(
                {"$ref": f"#/definitions/{type_name}", "definitions": schema["definitions"]})
        errors = sorted(validators[type_name].iter_errors(payload), key=lambda e: list(e.absolute_path))
        details = "\n  ".join(f"{'/'.join(map(str, e.absolute_path)) or '(racine)'} : {e.message}" for e in errors[:8])
        assert not errors, f"{label or type_name} non conforme au contrat mobile {type_name} :\n  {details}"

    return check


@pytest.fixture(scope="session")
def service(workspace):
    from easytrade.agents.simulated import simulated_client
    from easytrade.api.service import ApiService

    return ApiService(workspace=workspace, client=simulated_client())


@pytest.fixture(scope="session")
def api(service):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from easytrade.api.app import create_app

    return TestClient(create_app(service))


@pytest.fixture(scope="session")
def finished_run(api):
    """Lance une analyse par l'API et attend sa fin ; résultats mis en cache par session."""
    cache = {}

    def run(profile_id, ticker=None, as_of=None):
        key = (profile_id, ticker, as_of)
        if key not in cache:
            body = {"profile_id": profile_id}
            if ticker:
                body["requested_ticker"] = ticker
            if as_of:
                body["as_of"] = as_of
            response = api.post("/runs", json=body)
            assert response.status_code == 200, response.text
            run_id = response.json()["run_id"]
            deadline = time.time() + 60
            while True:
                status = api.get(f"/runs/{run_id}").json()
                if status["status"] != "en_cours":
                    break
                assert time.time() < deadline, f"analyse {run_id} non terminée en 60 s"
                time.sleep(0.02)
            cache[key] = status
        return cache[key]

    return run


def cited_evidence_ids(payload) -> list[str]:
    """Tous les identifiants de preuves cités dans une réponse (`evidence_ids`, `evidence_id`)."""
    found: dict[str, None] = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "evidence_ids" and isinstance(value, list):
                    found.update(dict.fromkeys(value))
                elif key == "evidence_id" and isinstance(value, str):
                    found[value] = None
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return list(found)
