"""Contraintes dures : admissibles et rejets motivés.

Conception : docs/03_DECISION_ENGINE.md
"""
import pandas as pd

from easytrade.engine.constraints import screen_assets
from easytrade.schemas.weights import ProfileWeights

PERSONAS = {
    "amira": {
        "id": "amira",
        "poids": {"croissance": 0.3, "stabilite": 0.1, "diversification": 0.2,
                  "esg": 0.05, "qualite": 0.1, "horizon": 0.1, "preferences": 0.15},
        "contraintes": {"max_weight_per_asset": 0.15, "max_weight_per_sector": 0.4,
                        "max_weight_crypto": 0.15, "esg_exclusion": False, "speculatif": "permis"},
    },
    "mateo": {
        "id": "mateo",
        "poids": {"croissance": 0.15, "stabilite": 0.2, "diversification": 0.15,
                  "esg": 0.25, "qualite": 0.15, "horizon": 0.05, "preferences": 0.05},
        "contraintes": {"max_weight_per_asset": 0.1, "max_weight_per_sector": 0.3,
                        "max_weight_crypto": 0.0, "esg_exclusion": True, "speculatif": "exclu"},
    },
}

UNIVERSE = pd.DataFrame([
    {"asset_id": "A1", "ticker": "AAPL", "name": "Apple", "asset_class": "equity",
     "market": "NASDAQ", "currency": "USD", "sector": "Information Technology"},
    {"asset_id": "A2", "ticker": "XOM", "name": "Exxon", "asset_class": "equity",
     "market": "NYSE", "currency": "USD", "sector": "Energy"},
    {"asset_id": "A3", "ticker": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto",
     "market": "Crypto", "currency": "USD", "sector": "Crypto asset"},
])


def test_constraints_crypto_excluded_for_mateo():
    pw = ProfileWeights.from_persona(PERSONAS["mateo"])
    result = screen_assets(UNIVERSE, pw.constraints)

    eligible = {a.ticker for a in result.eligible}
    rejected = {r.ticker: r for r in result.rejected}

    assert "BTC-USD" not in eligible
    assert "BTC-USD" in rejected
    # La crypto est écartée d'abord par la règle crypto (part max en crypto = 0).
    assert rejected["BTC-USD"].rule == "max_weight_crypto"
    assert rejected["BTC-USD"].reason  # motif non vide, montré à l'utilisateur
    assert eligible == {"AAPL", "XOM"}


def test_constraints_crypto_allowed_for_amira():
    pw = ProfileWeights.from_persona(PERSONAS["amira"])
    result = screen_assets(UNIVERSE, pw.constraints)

    assert {a.ticker for a in result.eligible} == {"AAPL", "XOM", "BTC-USD"}
    assert result.rejected == ()
    # Spéculatif « permis » → aucun drapeau.
    assert result.flags == {}


def test_constraints_speculative_flagged_not_rejected():
    persona = dict(PERSONAS["amira"])
    persona["contraintes"] = {**persona["contraintes"], "speculatif": "signalé"}
    pw = ProfileWeights.from_persona(persona)

    result = screen_assets(UNIVERSE, pw.constraints)

    assert "BTC-USD" in {a.ticker for a in result.eligible}
    assert "spéculatif signalé" in result.flags["BTC-USD"]


def test_constraints_esg_exclusion_uses_controversy_set():
    pw = ProfileWeights.from_persona(PERSONAS["mateo"])
    result = screen_assets(UNIVERSE, pw.constraints, esg_controversial=frozenset({"XOM"}))

    rejected = {r.ticker: r for r in result.rejected}
    assert rejected["XOM"].rule == "esg_exclusion"
    assert "AAPL" in {a.ticker for a in result.eligible}
