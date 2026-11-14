"""S4 — « Aucune recommandation » est une sortie valide.

Conception : docs/09_SCENARIOS_TEST.md, docs/03_DECISION_ENGINE.md
Deux chemins : plus aucun actif admissible, et preuves insuffisantes sur les actifs admissibles.
"""
import pandas as pd
import pytest

from easytrade.engine.decision import decide
from easytrade.schemas.weights import CRITERIA, ProfileWeights

AS_OF = "2026-11-12"

MATEO = {
    "id": "mateo",
    "poids": {"croissance": 0.15, "stabilite": 0.2, "diversification": 0.15,
              "esg": 0.25, "qualite": 0.15, "horizon": 0.05, "preferences": 0.05},
    "contraintes": {"max_weight_per_asset": 0.1, "max_weight_per_sector": 0.3,
                    "max_weight_crypto": 0.0, "esg_exclusion": True, "speculatif": "exclu"},
}

AMIRA = {
    "id": "amira",
    "poids": {"croissance": 0.3, "stabilite": 0.1, "diversification": 0.2,
              "esg": 0.05, "qualite": 0.1, "horizon": 0.1, "preferences": 0.15},
    "contraintes": {"max_weight_per_asset": 0.15, "max_weight_per_sector": 0.4,
                    "max_weight_crypto": 0.15, "esg_exclusion": False, "speculatif": "permis"},
}

CRYPTO_ONLY = pd.DataFrame([
    {"asset_id": "A30", "ticker": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto",
     "market": "Crypto", "currency": "USD", "sector": "Crypto asset"},
    {"asset_id": "A31", "ticker": "ETH-USD", "name": "Ether", "asset_class": "crypto",
     "market": "Crypto", "currency": "USD", "sector": "Crypto asset"},
])

EQUITIES = pd.DataFrame([
    {"asset_id": "A11", "ticker": "AAPL", "name": "Apple", "asset_class": "equity",
     "market": "NASDAQ", "currency": "USD", "sector": "Information Technology"},
    {"asset_id": "A20", "ticker": "XOM", "name": "Exxon", "asset_class": "equity",
     "market": "NYSE", "currency": "USD", "sector": "Energy"},
])


@pytest.mark.scenario("S4")
def test_s04_no_candidate_passes_hard_constraints():
    pw = ProfileWeights.from_persona(MATEO)
    decision = decide(CRYPTO_ONLY, signals={}, evidence={}, profile_weights=pw, as_of=AS_OF)

    assert decision.no_recommendation is True
    assert decision.ranking == ()
    assert len(decision.rejected) == 2            # chaque actif écarté est motivé
    assert "contrainte" in decision.reason.lower()


@pytest.mark.scenario("S4")
def test_s04_insufficient_evidence_yields_no_recommendation():
    pw = ProfileWeights.from_persona(AMIRA)
    # Actifs admissibles mais aucun signal exploitable.
    empty_signals = {t: {c: None for c in CRITERIA} for t in ("AAPL", "XOM")}
    empty_evidence = {t: {c: None for c in CRITERIA} for t in ("AAPL", "XOM")}

    decision = decide(EQUITIES, empty_signals, empty_evidence, pw, AS_OF)

    assert decision.no_recommendation is True
    assert "insuffisantes" in decision.reason.lower()
