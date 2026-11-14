"""« Tester une idée » : tensions chiffrées, verdict, effet sur le panier simulé, alternatives.

Conception : docs/03_DECISION_ENGINE.md (section « Demande explicite de l'utilisateur »)
Le moteur ne filtre pas en silence : quand l'utilisateur soumet un titre, il explicite chaque
écart avec le profil, rend un verdict, et propose des alternatives moins tendues si la preuve
existe. C'est la réponse au test Robert.
"""
from __future__ import annotations

import statistics
from typing import Optional

import pandas as pd

from easytrade.data.point_in_time import DateLike
from easytrade.engine.constraints import screen_assets
from easytrade.engine.decision import decide
from easytrade.schemas.coherence import CoherenceReport, Tension
from easytrade.schemas.weights import ProfileWeights

# Un titre dont la volatilité dépasse la médiane des pistes retenues de ce facteur est « tendu ».
VOL_TENSION_RATIO = 1.25


def _signal(signals: dict, ticker: str, criterion: str) -> Optional[float]:
    value = signals.get(ticker, {}).get(criterion)
    return float(value) if isinstance(value, (int, float)) else None


def evaluate_idea(
    ticker: str,
    assets: pd.DataFrame,
    signals: dict[str, dict[str, Optional[float]]],
    evidence: dict[str, dict[str, Optional[str]]],
    profile_weights: ProfileWeights,
    as_of: DateLike,
    *,
    esg_controversial: frozenset[str] = frozenset(),
) -> CoherenceReport:
    """Analyse de cohérence d'un titre soumis, par rapport aux contraintes et aux pistes retenues."""
    row = assets[assets["ticker"] == ticker]
    if row.empty:
        return CoherenceReport(
            ticker=ticker,
            verdict="incohérent avec le profil",
            tensions=(Tension(dimension="univers", detail="Titre absent de l'univers analysé."),),
        )

    tensions: list[Tension] = []

    # 1. Contraintes dures : une exclusion est une incohérence franche.
    screening = screen_assets(row, profile_weights.constraints, esg_controversial)
    for rejection in screening.rejected:
        tensions.append(Tension(dimension="contrainte", detail=rejection.reason, severe=True))

    # Contexte : pistes retenues pour ce profil (sert de référence de comparaison).
    decision = decide(assets, signals, evidence, profile_weights, as_of,
                      esg_controversial=esg_controversial)
    retained = [c.ticker for c in decision.ranking if c.ticker != ticker]

    # 2. Volatilité : signal « stabilite » orienté = -volatilité. Plus bas (plus négatif) = plus volatil.
    idea_stab = _signal(signals, ticker, "stabilite")
    retained_stab = [s for s in (_signal(signals, t, "stabilite") for t in retained) if s is not None]
    if idea_stab is not None and retained_stab:
        idea_vol = -idea_stab
        median_vol = -statistics.median(retained_stab)
        if median_vol > 0 and idea_vol > median_vol * VOL_TENSION_RATIO:
            tensions.append(Tension(
                dimension="volatilité",
                detail=(
                    f"Volatilité annualisée {idea_vol:.0f} % contre une médiane de {median_vol:.0f} % "
                    "pour les pistes retenues de votre profil."
                ),
                severe=idea_vol > median_vol * VOL_TENSION_RATIO * 1.5,
                evidence_id=evidence.get(ticker, {}).get("stabilite"),
            ))

    # 3. Horizon : pire période glissante sur 3 ans (signal orienté, plus bas = pire).
    idea_hz = _signal(signals, ticker, "horizon")
    retained_hz = [s for s in (_signal(signals, t, "horizon") for t in retained) if s is not None]
    if idea_hz is not None and retained_hz and idea_hz < statistics.median(retained_hz):
        tensions.append(Tension(
            dimension="horizon",
            detail=(
                f"Pire période glissante sur 3 ans {idea_hz:.0f} %, sous la médiane "
                f"{statistics.median(retained_hz):.0f} % des pistes retenues."
            ),
            evidence_id=evidence.get(ticker, {}).get("horizon"),
        ))

    # Verdict.
    severe = any(t.severe for t in tensions)
    if severe:
        verdict = "incohérent avec le profil"
    elif tensions:
        verdict = "cohérent avec réserve"
    else:
        verdict = "cohérent"

    # Alternatives : pistes retenues du même secteur, mieux classées, donc moins tendues.
    sector = str(row.iloc[0]["sector"])
    alternatives = tuple(
        c.ticker for c in decision.ranking
        if c.ticker != ticker and c.sector == sector
    )[:3]

    context = (
        f"{len(retained)} pistes retenues servent de référence ; "
        f"confiance du profil : {decision.confidence}."
    )
    return CoherenceReport(
        ticker=ticker,
        verdict=verdict,
        tensions=tuple(tensions),
        context=context,
        alternatives=alternatives,
    )
