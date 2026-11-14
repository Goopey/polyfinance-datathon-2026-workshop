"""S12 — Même univers, profils différents, classements différents et expliqués.

Conception : docs/09_SCENARIOS_TEST.md, docs/03_DECISION_ENGINE.md
Utilise les vraies données du socle (P1) : indicateurs réels → signaux → décision.
"""
import pytest

from easytrade.engine.decision import decide
from easytrade.engine.signals import build_signals
from easytrade.schemas.weights import CRITERIA, ProfileWeights

# Sous-ensemble contrasté : croissance/tech, valeurs stables, obligations, or.
SUBSET = ["NVDA", "SHOP.TO", "AAPL", "RY.TO", "FTS.TO", "XBB.TO", "TLT", "GLD"]


def _persona(personas, persona_id):
    return next(p for p in personas["personas"] if p["id"] == persona_id)


@pytest.fixture(scope="module")
def decided(store, registry, settings, personas):
    from easytrade.explain.evidence_ledger import EvidenceLedger
    from easytrade.validation.metrics import compute_metrics_table

    assets = store.assets()
    subset = assets[assets["ticker"].isin(SUBSET)].reset_index(drop=True)

    ledger = EvidenceLedger(settings.as_of)
    metrics = compute_metrics_table(store, settings.as_of, ledger, registry, tickers=SUBSET)
    signals, evidence = build_signals(metrics, subset)

    def run(persona_id):
        pw = ProfileWeights.from_persona(_persona(personas, persona_id))
        return decide(subset, signals, evidence, pw, settings.as_of)

    return run


@pytest.mark.scenario("S12")
def test_s12_rankings_differ_between_personas(decided):
    amira = decided("amira")
    robert = decided("robert")

    assert not amira.no_recommendation
    assert not robert.no_recommendation

    order_amira = [c.ticker for c in amira.ranking]
    order_robert = [c.ticker for c in robert.ranking]

    # Même univers admissible, mais classement différent : la pondération du profil agit.
    assert set(order_amira) == set(order_robert)
    assert order_amira != order_robert


@pytest.mark.scenario("S12")
def test_s12_rankings_are_explained_by_contributions(decided):
    amira = decided("amira")
    pw = ProfileWeights.from_persona({
        "id": "amira",
        "poids": dict(zip(CRITERIA, [0.3, 0.1, 0.2, 0.05, 0.1, 0.1, 0.15])),
        "contraintes": {"max_weight_per_asset": 0.15, "max_weight_per_sector": 0.4,
                        "max_weight_crypto": 0.15, "esg_exclusion": False, "speculatif": "permis"},
    })

    top = amira.ranking[0]
    # Chaque piste expose les sept contributions, et leur somme est le score d'adéquation.
    assert tuple(cs.criterion for cs in top.criteria) == CRITERIA
    assert sum(cs.contribution for cs in top.criteria) == pytest.approx(top.fit_score)
    # Les poids rattachés aux critères sont bien ceux du profil Amira.
    weights = {cs.criterion: cs.weight for cs in top.criteria}
    assert weights == pw.weights


@pytest.mark.scenario("S12")
def test_s12_is_deterministic(decided):
    first = [c.ticker for c in decided("robert").ranking]
    second = [c.ticker for c in decided("robert").ranking]
    assert first == second
