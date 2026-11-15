"""Scores par critère (rang centile) et score d'adéquation pondéré ; contributions conservées.

Conception : docs/03_DECISION_ENGINE.md (sections « Score d'adéquation » et « Critères »)
    score(a) = Σ_k  w_k · s_k(a)      avec Σ w_k = 1 et s_k(a) ∈ [0, 1]
- s_k est le rang centile du signal dans l'univers à la date `as_of` : il évite de comparer des
  unités différentes et reste borné. Exception : le critère `esg`, catégoriel, est noté en absolu
  (`ABSOLUTE_CRITERIA`, engine/esg.py).
- Un signal manquant n'est jamais un bon score : s_k = 0 et le critère est marqué « manquant »
  (il abaisse aussi la confiance, voir decision.py).
- La contribution w_k · s_k est conservée critère par critère pour l'explication.
Python déterministe : mêmes entrées, même sortie ; départage final par ticker.
"""
from __future__ import annotations

import math
from typing import Optional

from easytrade.schemas.candidate import Asset, CriterionScore, ScoredCandidate
from easytrade.engine.constraints import RISK_FLAG
from easytrade.engine.signals import applicable
from easytrade.schemas.weights import CRITERIA

# Critères catégoriels notés en absolu (engine/esg.py) : sur deux catégories (préoccupation documentée = 0,
# filtre ESG documenté = 1), un rang centile placerait la préoccupation documentée au-dessus d'un inconnu.
ABSOLUTE_CRITERIA = frozenset({"esg"})


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


# Seuils du libellé d'adéquation (hypothèses de l'équipe, docs/03_DECISION_ENGINE.md).
FIT_HIGH = 0.65
FIT_PARTIAL = 0.50


def fit_level(candidate: ScoredCandidate) -> str:
    """Adéquation au profil : « élevée », « partielle » ou « faible ».

    Le score est rapporté au poids des critères réellement couverts pour ce candidat : un
    critère sans donnée ne fait pas baisser le libellé (il baisse la confiance, affichée à part).
    """
    applicable_weight = sum(c.weight for c in candidate.criteria if c.applicable)
    covered = sum(c.weight for c in candidate.criteria if c.applicable and not c.missing)
    if covered <= 0:
        return "faible"
    relative = candidate.fit_score * applicable_weight / covered  # fit_score est déjà rapporté aux critères applicables
    # Un actif qui dépasse un repère de risque du profil (sans être écarté) ne peut pas être « élevée ».
    beyond_risk = RISK_FLAG in candidate.flags
    if relative >= FIT_HIGH and not beyond_risk:
        return "élevée"
    return "partielle" if relative >= FIT_PARTIAL else "faible"


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

    # Rang centile par critère, calculé sur les actifs admissibles ; score absolu pour les critères
    # catégoriels (`ABSOLUTE_CRITERIA`), dont le signal est déjà un score dans [0, 1].
    ranks: dict[str, dict[str, Optional[float]]] = {}
    for criterion in CRITERIA:
        per_ticker = {t: signals.get(t, {}).get(criterion) for t in tickers}
        if criterion in ABSOLUTE_CRITERIA:
            ranks[criterion] = {t: (min(1.0, max(0.0, float(v))) if _is_number(v) else None)
                                for t, v in per_ticker.items()}
        else:
            ranks[criterion] = percentile_rank(per_ticker)

    scored: list[ScoredCandidate] = []
    for asset in eligible:
        criteria_scores: list[CriterionScore] = []
        missing: list[str] = []
        # Critère non applicable à la classe d'actifs : retiré, poids réparti sur les autres critères.
        applicable_weight = sum(float(weights[c]) for c in CRITERIA if applicable(c, asset.asset_class))
        scale = 1.0 / applicable_weight if applicable_weight > 0 else 0.0
        fit = 0.0
        for criterion in CRITERIA:
            weight = float(weights[criterion])
            signal = signals.get(asset.ticker, {}).get(criterion)
            is_applicable = applicable(criterion, asset.asset_class)
            rank = ranks[criterion].get(asset.ticker) if is_applicable else None
            if not is_applicable:
                score, is_missing = 0.0, False
            elif rank is None:
                score = 0.0
                missing.append(criterion)
                is_missing = True
            else:
                score = float(rank)
                is_missing = False
            contribution = weight * score * scale if is_applicable else 0.0
            fit += contribution
            criteria_scores.append(CriterionScore(
                criterion=criterion,
                signal=None if not _is_number(signal) or not is_applicable else float(signal),
                score=score,
                weight=weight,
                contribution=contribution,
                missing=is_missing,
                evidence_id=evidence.get(asset.ticker, {}).get(criterion) if is_applicable else None,
                applicable=is_applicable,
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
