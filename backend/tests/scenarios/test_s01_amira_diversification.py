"""S1 — Amira : le risque élevé garde une diversification.

Conception : docs/09_SCENARIOS_TEST.md
Pipeline complet en local sur les données réelles du jeu de départ, agents simulés (aucun modèle).
Le classement, les plafonds et les déclassements sont produits par le moteur déterministe.
"""
import pytest

from easytrade.engine.governance import TECHNOLOGY_GROUP, basket_shares, concentration_group
from easytrade.engine.signals import asset_themes


@pytest.fixture(scope="module")
def run(pipeline_run):
    result = pipeline_run("amira")
    assert result.status == "termine", result.error
    return result


@pytest.mark.scenario("S1")
def test_s01_1_des_pistes_technologiques_ou_crypto_apparaissent(run):
    items = run.explanation.items
    offensive = [i.ticker for i in items
                 if "technologies" in asset_themes(i.asset_class, i.sector) or i.asset_class == "crypto"]
    assert offensive, "le profil offensif n'est pas respecté : aucune piste technologique ni crypto"


@pytest.mark.scenario("S1")
def test_s01_2_plafonds_tenus(run):
    constraints = run.weighting.profile_weights.constraints
    retained = [c for c in run.decision.ranking if c.ticker in run.decision.retained]
    shares = basket_shares(retained)
    assert shares["per_asset"] <= constraints.max_weight_per_asset + 1e-9
    assert max(shares["per_sector"].values()) <= constraints.max_weight_per_sector + 1e-9
    assert shares["crypto"] <= constraints.max_weight_crypto + 1e-9
    controls = {s.step: s for s in run.trace.steps if s.kind == "controle"}
    assert controls["controle.plafonds_panier"].status == "ok"
    assert controls["controle.diversification"].status == "ok"


@pytest.mark.scenario("S1")
def test_s01_3_au_moins_trois_secteurs_hors_technologies(run):
    groups = {concentration_group(i.sector) for i in run.explanation.items}
    assert len(groups - {TECHNOLOGY_GROUP}) >= 3, groups
    # Échec type du scénario : une liste composée uniquement de technologies et de crypto.
    assert any(concentration_group(i.sector) != TECHNOLOGY_GROUP and i.asset_class != "crypto"
               for i in run.explanation.items)


@pytest.mark.scenario("S1")
def test_s01_4_et_5_un_candidat_declasse_pour_concentration_motif_rattache_au_profil(run):
    displaced = [r for r in run.explanation.rejected if r.kind == "classement"]
    assert displaced, "aucun candidat déclassé pour concentration"
    item = displaced[0]
    assert "concentration" in item.reason
    assert item.ticker not in {i.ticker for i in run.explanation.items}
    # Le motif cite la règle (hypothèse chiffrée) et la phrase du profil à l'origine de la règle.
    statements = [run.ledger.get(i).statement for i in item.evidence_ids]
    assert any("Part maximale par secteur" in s for s in statements)
    assert any("Préférence déclarée" in s and "diversification" in s for s in statements), statements
    # La justification de l'agent de pondération relie bien le plafond au souhait de diversification.
    origin = run.weighting.rationale_evidence("hard_constraints.max_weight_per_sector")
    assert origin and "diversification" in run.ledger.get(origin[0]).statement


@pytest.mark.scenario("S1")
def test_s01_chaque_piste_est_expliquee_et_debattue(run):
    for item in run.explanation.items:
        assert item.why, item.ticker
        assert {p.agent for p in item.debate} == {"bull", "realist", "bear"}
        assert set(item.contributions) == set(run.weighting.profile_weights.weights)
