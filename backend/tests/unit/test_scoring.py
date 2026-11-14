"""Score pondéré, contributions, normalisation par rang centile.

Conception : docs/03_DECISION_ENGINE.md
"""
import math

from easytrade.engine.scoring import percentile_rank, score_candidates
from easytrade.schemas.candidate import Asset
from easytrade.schemas.weights import CRITERIA

WEIGHTS = {
    "croissance": 0.4,
    "stabilite": 0.2,
    "diversification": 0.1,
    "esg": 0.1,
    "qualite": 0.1,
    "horizon": 0.1,
    "preferences": 0.0,
}


def _asset(ticker, sector="S", asset_class="equity"):
    return Asset(asset_id=ticker, ticker=ticker, name=ticker, asset_class=asset_class,
                 market="M", currency="CAD", sector=sector)


def test_percentile_rank_orders_and_bounds():
    ranks = percentile_rank({"low": 1.0, "mid": 2.0, "high": 3.0})
    assert ranks["low"] < ranks["mid"] < ranks["high"]
    assert all(0.0 < r < 1.0 for r in ranks.values())


def test_percentile_rank_handles_ties_and_missing():
    ranks = percentile_rank({"a": 5.0, "b": 5.0, "c": None})
    assert ranks["a"] == ranks["b"]        # égalité → même rang
    assert ranks["c"] is None              # manquant reste manquant


def _uniform_signal(value, missing=()):
    """Un jeu de signaux complet avec une même valeur, certains critères forcés manquants."""
    return {c: (None if c in missing else value) for c in CRITERIA}


def test_scoring_contributions_sum_to_fit_score():
    eligible = (_asset("A"), _asset("B"), _asset("C"))
    signals = {
        "A": _uniform_signal(0.1),
        "B": _uniform_signal(0.3),
        "C": _uniform_signal(0.2),
    }
    evidence = {t: {c: None for c in CRITERIA} for t in signals}

    scored = score_candidates(eligible, signals, evidence, WEIGHTS)

    for candidate in scored:
        total = sum(cs.contribution for cs in candidate.criteria)
        assert math.isclose(total, candidate.fit_score, abs_tol=1e-9)
        for cs in candidate.criteria:
            assert math.isclose(cs.contribution, cs.weight * cs.score, abs_tol=1e-12)


def test_scoring_ranks_higher_signal_first():
    eligible = (_asset("A"), _asset("B"), _asset("C"))
    signals = {"A": _uniform_signal(0.1), "B": _uniform_signal(0.3), "C": _uniform_signal(0.2)}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}

    scored = score_candidates(eligible, signals, evidence, WEIGHTS)

    assert [c.ticker for c in scored] == ["B", "C", "A"]


def test_scoring_missing_signal_scores_zero_and_is_flagged():
    eligible = (_asset("A"), _asset("B"))
    # esg manquant pour tous → score 0 et marqué manquant, jamais un bon score.
    signals = {"A": _uniform_signal(0.2, missing=("esg",)),
               "B": _uniform_signal(0.3, missing=("esg",))}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}

    scored = score_candidates(eligible, signals, evidence, WEIGHTS)

    for candidate in scored:
        esg = next(cs for cs in candidate.criteria if cs.criterion == "esg")
        assert esg.missing is True
        assert esg.score == 0.0
        assert esg.contribution == 0.0
        assert "esg" in candidate.missing_criteria


def test_scoring_is_deterministic():
    eligible = (_asset("A"), _asset("B"), _asset("C"))
    signals = {"A": _uniform_signal(0.1), "B": _uniform_signal(0.3), "C": _uniform_signal(0.2)}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}

    first = score_candidates(eligible, signals, evidence, WEIGHTS)
    second = score_candidates(eligible, signals, evidence, WEIGHTS)
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]
