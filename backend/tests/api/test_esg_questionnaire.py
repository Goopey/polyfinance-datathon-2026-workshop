"""Questionnaire et ESG : poids ESG selon l'intérêt déclaré, preuve par esg_evidence.csv, avertissement.

Conception : docs/03_DECISION_ENGINE.md (section « Critère ESG »)
"""
import pytest

DRAFT = {"objectif": "equilibre", "horizon": "moyen", "exclusions": []}


def _profile(api, tolerance, preferences):
    response = api.post("/profiles", json={**DRAFT, "tolerance": tolerance, "preferences": preferences})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("tolerance", ["faible", "moderee", "elevee"])
def test_esg_seul_interet_devient_le_critere_le_plus_important(api, tolerance):
    weights = _profile(api, tolerance, ["esg"])["weights"]
    assert weights["esg"] >= 0.30
    assert all(weights["esg"] > w for c, w in weights.items() if c != "esg")
    assert sum(weights.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("tolerance", ["faible", "moderee", "elevee"])
def test_interet_esg_parmi_d_autres_porte_le_poids_a_25(api, tolerance):
    body = _profile(api, tolerance, ["esg", "technologies"])
    assert body["weights"]["esg"] == pytest.approx(0.25, abs=1e-6)


def test_sans_interet_esg_le_poids_revient_a_5(api):
    """Le gabarit « modéré » est Mateo (ESG 25 % pour sa phrase sur l'ESG) : sans case cochée, 5 %."""
    body = _profile(api, "moderee", ["stabilite"])
    assert body["weights"]["esg"] == pytest.approx(0.05, abs=1e-6)
    assert any("Aucun intérêt ESG déclaré" in r["because"] for r in body["rationale"])


def test_esg_seul_le_titre_prouve_par_le_fichier_est_en_tete(api, finished_run):
    profile = _profile(api, "moderee", ["esg"])
    status = finished_run(profile["profile_id"])
    assert status["status"] == "termine", status["error"]
    result = status["result"]
    assert result["items"][0]["ticker"] == "ESGV" and result["warnings"] == []
    # Émetteurs majeurs documentés écartés (le gabarit « modéré » porte aussi l'exclusion des controverses de Mateo).
    reasons = {r["ticker"]: r["reason"] for r in result["rejected"]}
    assert "émetteur majeur" in reasons["XOM"] and "émetteur majeur" in reasons["CNQ.TO"]


def test_esg_seul_sans_exclusion_ecarte_les_emetteurs_majeurs(api, finished_run):
    """Profil offensif (gabarit sans exclusion ESG) : c'est la grande importance donnée à l'ESG qui écarte XOM."""
    status = finished_run(_profile(api, "elevee", ["esg"])["profile_id"])
    assert status["status"] == "termine", status["error"]
    reasons = {r["ticker"]: r["reason"] for r in status["result"]["rejected"]}
    assert "grande importance à l'ESG" in reasons["XOM"]
    assert not {"XOM", "CNQ.TO"} & {i["ticker"] for i in status["result"]["items"]}


def test_esg_seul_sans_titre_prouve_admissible_pistes_et_avertissement(api, finished_run):
    """Tolérance faible : ESGV dépasse les repères de risque ; les pistes restent, avec un avertissement."""
    profile = _profile(api, "faible", ["esg"])
    status = finished_run(profile["profile_id"])
    assert status["status"] == "termine", status["error"]
    result = status["result"]
    assert not result["no_recommendation"] and result["items"]
    assert "ESGV" not in {i["ticker"] for i in result["items"]}
    assert any("ESGV (écarté par une règle de votre profil)" in w for w in result["warnings"])
    assert all(i["confidence"] == "faible" for i in result["items"])
    assert not {"XOM", "CNQ.TO"} & {i["ticker"] for i in result["items"]}
