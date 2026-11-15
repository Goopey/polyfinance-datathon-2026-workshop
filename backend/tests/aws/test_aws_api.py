"""P4 — L'API sur AWS : runs dans la table, lancement par la machine d'états, résultat lu sur S3.

Conception : api/aws_service.py
Le lanceur Step Functions est remplacé par l'interpréteur de la machine d'états (exécution synchrone).
Deux instances du service jouent deux conteneurs Lambda : rien ne doit dépendre de la mémoire.
"""
import pytest

from easytrade.api.aws_service import AwsApiService, StepFunctionsLauncher
from easytrade.orchestration import aws_runtime
from easytrade.schemas.api import ProfileDraft, RunRequest
from tests.aws.asl_runner import AslRunner, ExecutionFailed
from tests.aws.test_state_machine import ASL, RESOURCES, aws_env  # noqa: F401  (fixture)


class Launcher:
    def __init__(self):
        self.payloads = []

    def __call__(self, run_id, payload):
        self.payloads.append(payload)
        try:
            AslRunner(ASL, RESOURCES).run(payload)
        except ExecutionFailed:
            pass  # l'échec est inscrit dans la table, comme sur AWS


@pytest.fixture
def services(aws_env, workspace):  # noqa: F811
    launcher = Launcher()

    def make():
        return AwsApiService(workspace=workspace, client=aws_runtime.llm(), table=aws_runtime.run_table(),
                             store=aws_runtime.state_store(), launcher=launcher)

    return make, launcher


def test_run_lance_par_la_machine_et_lu_par_un_autre_conteneur(services):
    make, launcher = services
    first, second = make(), make()
    run_id = first.start_run(RunRequest(profile_id="robert", requested_ticker="TSLA"))

    status = second.run_status(run_id)  # autre conteneur : lit la table et S3, pas la mémoire
    assert status.status == "termine"
    assert [s.status for s in status.steps] == ["ok"] * len(status.steps)
    assert status.result is not None and status.result.coherence.verdict == "incohérent avec le profil"
    assert launcher.payloads[0]["persona"] is None  # persona de l'énoncé : pas besoin de la transmettre
    evidence_id = status.result.items[0].why[0].evidence_ids[0]
    assert second.evidence(evidence_id, run_id=run_id).evidence_id == evidence_id
    assert second.trace(run_id).steps


def test_run_identique_reutilise(services):
    make, launcher = services
    service = make()
    first = service.start_run(RunRequest(profile_id="amira"))
    again = service.start_run(RunRequest(profile_id="amira"))
    assert first == again and len(launcher.payloads) == 1


def test_profil_fictif_transmis_a_l_execution(services):
    make, launcher = services
    creator, runner = make(), make()
    view = creator.create_profile(ProfileDraft(tolerance="elevee", horizon="long", objectif="croissance",
                                               preferences=["technologies"], exclusions=["crypto"]))
    run_id = runner.start_run(RunRequest(profile_id=view.profile_id))  # profil retrouvé dans la table

    assert launcher.payloads[0]["persona"]["id"] == view.profile_id
    assert launcher.payloads[0]["profile_source"] == "profil_questionnaire"
    status = runner.run_status(run_id)
    assert status.status == "termine"
    assert not any(item.ticker in ("BTC-USD", "ETH-USD") for item in status.result.items)  # exclusion appliquée


def test_echec_de_lancement_visible(services):
    make, _ = services

    def refuse(run_id, payload):
        raise RuntimeError("AccessDenied")

    service = make()
    service.launch = refuse
    with pytest.raises(RuntimeError):
        service.start_run(RunRequest(profile_id="mateo"))
    status = service.run_status("run_2026-11-12_mateo")
    assert status.status == "echec" and "AccessDenied" in status.error


def test_lanceur_step_functions_nom_unique_et_valide():
    class FakeSfn:
        def __init__(self):
            self.calls = []

        def start_execution(self, **kwargs):
            self.calls.append(kwargs)
            return {"executionArn": "arn:exec"}

    sfn = FakeSfn()
    launcher = StepFunctionsLauncher("arn:aws:states:us-east-1:1:stateMachine:easytrade", client=sfn)
    launcher("run_2026-11-12_robert_RY.TO", {"run_id": "run_2026-11-12_robert_RY.TO"})
    launcher("run_2026-11-12_robert_RY.TO", {"run_id": "run_2026-11-12_robert_RY.TO"})
    names = [c["name"] for c in sfn.calls]
    assert names[0] != names[1] and all(len(n) <= 80 for n in names)
    assert all(set(n) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_") for n in names)
