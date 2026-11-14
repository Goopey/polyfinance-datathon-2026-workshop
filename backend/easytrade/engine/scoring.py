"""Scores par critère (rang centile) et score d'adéquation pondéré ; contributions conservées.

Conception : docs/03_DECISION_ENGINE.md (sections « Score d'adéquation » et « Critères »)
    score(a) = Σ_k  w_k · s_k(a)      avec Σ w_k = 1 et s_k(a) ∈ [0, 1]
- s_k est le rang centile du signal dans l'univers à la date `as_of` : il évite de comparer des
  unités différentes et reste borné.
- Un signal manquant n'est jamais un bon score : s_k = 0 et le critère est marqué « manquant »
  (il abaisse aussi la confiance, voir decision.py).
- La contribution w_k · s_k est conservée critère par critère pour l'explication.
Python déterministe : mêmes entrées, même sortie ; départage final par ticker.
"""
from __future__ import annotations

import math
from typing import Optional

from easytrade.schemas.candidate import Asset, CriterionScore, ScoredCandidate
from easytrade.schemas.weights import CRITERIA


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value))


def percentile_rank(signals: dict[str, Optional[float]]) -> dict[str, Optional[float]]:
    """Rang centile « mi-rang » dans [0, 1] pour chaque ticker ; None reste None.

    score = (nb de valeurs strictement inférieures + 0,5 × nb d'égales) / N
    Les égalités partagent le même rang ; la valeur la plus haute obtient le score le plus élevé.
    """
    present = {t: float(v) for t, v in signals.items() if _is_number(v)}
    n = len(present)
    out: dict[str, Optional[float]] = {}
    for ticker, value in signals.items():
        if not _is_number(value):
            out[ticker] = None
            continue
        v = float(value)
        less = sum(1 for u in present.values() if u < v)
        equal = sum(1 for u in present.values() if u == v)
        out[ticker] = (less + 0.5 * equal) / n
    return out


def score_candidates(
    eligible: tuple[Asset, ...],
    signals: dict[str, dict[str, Optional[float]]],
    evidence: dict[str, dict[str, Optional[str]]],
    weights: dict[str, float],
    flags: Optional[dict[str, tuple[str, ...]]] = None,
) -> list[ScoredCandidate]:
    """Classe les actifs admissibles : score d'adéquation, contributions, critères manquants.

    La normalisation (rang centile) se fait **sur l'univers admissible** : on compare des actifs
    réellement éligibles au profil.
    """
    flags = flags or {}
    tickers = [asset.ticker for asset in eligible]

    # Rang centile par critère, calculé sur les actifs admissibles.
    ranks: dict[str, dict[str, Optional[float]]] = {}
    for criterion in CRITERIA:
        per_ticker = {t: signals.get(t, {}).get(criterion) for t in tickers}
        ranks[criterion] = percentile_rank(per_ticker)

    scored: list[ScoredCandidate] = []
    for asset in eligible:
        criteria_scores: list[CriterionScore] = []
        missing: list[str] = []
        fit = 0.0
        for criterion in CRITERIA:
            weight = float(weights[criterion])
            signal = signals.get(asset.ticker, {}).get(criterion)
            rank = ranks[criterion].get(asset.ticker)
            if rank is None:
                score = 0.0
                missing.append(criterion)
                is_missing = True
            else:
                score = float(rank)
                is_missing = False
            contribution = weight * score
            fit += contribution
            criteria_scores.append(CriterionScore(
                criterion=criterion,
                signal=None if not _is_number(signal) else float(signal),
                score=score,
                weight=weight,
                contribution=contribution,
                missing=is_missing,
                evidence_id=evidence.get(asset.ticker, {}).get(criterion),
            ))
        scored.append(ScoredCandidate(
            ticker=asset.ticker,
            name=asset.name,
            sector=asset.sector,
            asset_class=asset.asset_class,
            fit_score=fit,
            criteria=tuple(criteria_scores),
            missing_criteria=tuple(missing),
            flags=flags.get(asset.ticker, ()),
        ))

    # Classement déterministe : score décroissant, puis ticker croissant pour départager.
    scored.sort(key=lambda c: (-c.fit_score, c.ticker))
    return scored
