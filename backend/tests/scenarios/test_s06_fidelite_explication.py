"""S6 — Chaque nombre et chaque affirmation de l'explication est étayé.

Conception : docs/09_SCENARIOS_TEST.md, docs/05_EXPLICABILITE.md (section 4)
Deux volets :
- les runs des trois personas (données réelles, agents simulés) : contrôle indépendant de chaque
  affirmation de la sortie, et taux de réussite du vérificateur ;
- un agent d'explication fautif (nombre inventé, preuve inconnue, formulation prescriptive) :
  une relance, puis retrait des phrases fautives ; la sortie affichée reste fidèle.
"""
import pytest

from easytrade.agents.simulated import explanation as simulated_explanation
from easytrade.agents.simulated import simulated_client
from easytrade.explain.fidelity import explanation_claims, extract_numbers, number_supported, verify_explanation
from easytrade.orchestration.pipeline import run_pipeline

RUNS = [("amira", None), ("mateo", None), ("robert", None), ("robert", "TSLA")]


@pytest.fixture(scope="module", params=RUNS, ids=lambda p: "-".join(x for x in p if x))
def run(request, pipeline_run):
    result = pipeline_run(*request.param)
    assert result.status == "termine", result.error
    return result


def _ignore(workspace):
    assets = workspace.store.assets()
    return (*assets["name"].tolist(), *assets["ticker"].tolist())


@pytest.mark.scenario("S6")
def test_s06_1_chaque_nombre_correspond_a_une_preuve_citee(run, workspace):
    ignore = _ignore(workspace)
    for where, claim in explanation_claims(run.explanation):
        cited = [run.ledger.get(i) for i in claim.evidence_ids]
        for token in extract_numbers(claim.text, ignore):
            assert number_supported(token, cited), f"{where} : « {token} » non étayé dans « {claim.text} »"


@pytest.mark.scenario("S6")
def test_s06_2_chaque_affirmation_a_une_preuve_valide(run):
    claims = explanation_claims(run.explanation)
    for where, claim in claims:
        assert claim.evidence_ids, f"{where} sans preuve : {claim.text}"
        for evidence_id in claim.evidence_ids:
            assert evidence_id in run.ledger, f"{where} cite une preuve inconnue : {evidence_id}"
            assert run.ledger.get(evidence_id).published_at <= run.as_of


@pytest.mark.scenario("S6")
def test_s06_controle_independant_de_la_sortie(run, workspace):
    checked, issues = verify_explanation(run.explanation, run.ledger, workspace.forbidden, ignore=_ignore(workspace))
    assert issues == (), issues
    assert checked == run.fidelity.final_checked
    assert run.fidelity.faithful


@pytest.mark.scenario("S6")
def test_s06_3_taux_de_reussite_mesure_sur_les_trois_personas(pipeline_run, capsys):
    checked = ok = removed = final = 0
    lines = []
    for persona in ("amira", "mateo", "robert"):
        report = pipeline_run(persona).fidelity
        checked += report.first_pass_checked
        ok += report.first_pass_ok
        removed += report.removed
        final += report.final_checked
        rate = "sans objet" if report.first_pass_rate is None else f"{report.first_pass_rate:.0%}"
        lines.append(f"{persona}: {report.first_pass_ok}/{report.first_pass_checked} ({rate}), "
                     f"{report.final_checked} affirmations recontrôlées")
    with capsys.disabled():
        print("\n[S6] vérificateur de fidélité, agents simulés — " + " ; ".join(lines)
              + f" ; total {ok}/{checked}, {removed} retirée(s), {final} recontrôlées")
    assert checked > 0 and final > 0
    assert ok == checked and removed == 0  # agents simulés : aucune phrase fautive attendue


# --- agent d'explication fautif ---------------------------------------------------------------------
def _faulty(payload):
    """Rédaction fautive : nombre inventé, preuve inconnue, formulation prescriptive, aucune preuve."""
    draft = simulated_explanation(payload)
    for item in draft["items"]:
        evidence_id = item["why"][0]["evidence_ids"][0] if item["why"] else "EV-000001"
        item["why"] = [
            {"text": "Ce titre a gagné 87 % par an en moyenne.", "evidence_ids": [evidence_id], "claim_kind": "FAIT"},
            {"text": "Sa solidité financière est documentée.", "evidence_ids": ["EV-999999"], "claim_kind": "FAIT"},
            {"text": "Achetez ce titre : rendement garanti.", "evidence_ids": [evidence_id], "claim_kind": "FAIT"},
        ]
    # Trois raisons au plus par piste : sur la première, la phrase à preuve inconnue cède la place à une phrase sans preuve.
    draft["items"][0]["why"][1] = {"text": "Une valeur sûre selon les experts.", "evidence_ids": []}
    return draft


def _client(explanation_responder):
    client = simulated_client()
    client.responders["explanation"] = explanation_responder
    return client


@pytest.mark.scenario("S6")
def test_s06_phrases_fautives_retirees_apres_une_relance(workspace):
    client = _client(_faulty)
    result = run_pipeline("amira", client=client, workspace=workspace)
    assert result.status == "termine", result.error
    report, items = result.fidelity, result.explanation.items
    # Une relance exactement, avec le motif de chaque refus.
    explanation_calls = [c for c in client.calls if c["step"] == "explanation"]
    assert len(explanation_calls) == 2 and report.retried
    codes = {code for issue in report.issues for code in issue.codes}
    assert {"nombre_non_etaye", "preuve_inconnue", "formulation", "sans_preuve"} <= codes
    # Toutes les phrases fautives sont retirées ; l'incident est compté et inscrit dans la trace.
    assert report.first_pass_ok == 0 and report.first_pass_checked == 3 * len(items)
    assert report.removed == report.first_pass_checked
    text = result.explanation.model_dump_json()
    assert "87 %" not in text and "EV-999999" not in text and "garanti" not in text.lower()
    assert "experts" not in text and "solidité financière" not in text
    # Chaque piste garde une raison, recomposée par le code à partir d'une preuve ; la sortie reste fidèle.
    assert report.fallbacks == len(items) and all(len(i.why) == 1 for i in items)
    assert report.faithful
    steps = {s.step: s for s in result.trace.steps}
    assert "relance" in steps["explication"].note and steps["explication"].attempts == 2
    assert steps["controle.avant_affichage"].status == "ok" and "retirées" in steps["controle.avant_affichage"].note


@pytest.mark.scenario("S6")
def test_s06_relance_reussie_aucune_phrase_retiree(workspace):
    calls = {"n": 0}

    def faulty_then_correct(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            return _faulty(payload)
        assert payload["corrections"], "la relance doit recevoir le motif des refus"
        return simulated_explanation(payload)

    result = run_pipeline("amira", client=_client(faulty_then_correct), workspace=workspace)
    assert result.status == "termine", result.error
    report = result.fidelity
    assert report.retried and report.removed == 0 and report.fallbacks == 0
    assert report.first_pass_ok == 0 and report.faithful
    assert all(len(i.why) >= 1 for i in result.explanation.items)
