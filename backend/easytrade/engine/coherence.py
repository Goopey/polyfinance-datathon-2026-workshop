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
from easytrade.engine.constraints import (  # noqa: F401  (RISK_LIMITS, SEVERE_RATIO, tolerance_level : réexportés)
    RISK_LIMITS,
    SEVERE_RATIO,
    pct_fr,
    risk_breach,
    screen_assets,
    tolerance_level,
)
from easytrade.engine.decision import esg_focused, decide
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
    esg_emitters: frozenset[str] = frozenset(),
    risk: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = None,
    risk_level: Optional[str] = None,
    horizon_label: str = "3 ans",
) -> CoherenceReport:
    """Analyse de cohérence d'un titre soumis, par rapport aux contraintes et aux pistes retenues.

    `risk` et `risk_level` : mêmes repères que le classement (`decide`), pour que les pistes de référence
    soient celles que le profil reçoit vraiment. Les écarts aux repères eux-mêmes sont ajoutés par
    `limit_tensions` (pipeline), avec leurs preuves. `horizon_label` : fenêtre du critère horizon.
    """
    row = assets[assets["ticker"] == ticker]
    if row.empty:
        return CoherenceReport(
            ticker=ticker,
            verdict="incohérent avec le profil",
            tensions=(Tension(dimension="univers", detail="Titre absent de l'univers analysé."),),
        )

    tensions: list[Tension] = []

    # 1. Contraintes dures : une exclusion est une incohérence franche.
    screening = screen_assets(row, profile_weights.constraints, esg_controversial, esg_emitters=esg_emitters,
                              esg_focus=esg_focused(profile_weights.weights))
    for rejection in screening.rejected:
        tensions.append(Tension(dimension="contrainte", detail=rejection.reason, severe=True))

    # Contexte : pistes retenues pour ce profil (sert de référence de comparaison).
    decision = decide(assets, signals, evidence, profile_weights, as_of, esg_controversial=esg_controversial,
                      esg_emitters=esg_emitters, risk=risk, risk_level=risk_level)
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
                # Comparaison de contexte, pas une règle du profil : elle nuance le verdict sans le rendre
                # « incohérent ». Seules les règles et la tolérance au risque le font (même écran que le
                # classement, audit C2) ; sinon un titre admis par le classement serait jugé incohérent.
                severe=False,
                evidence_id=evidence.get(ticker, {}).get("stabilite"),
            ))

    # 3. Horizon : pire période glissante sur la fenêtre du profil (signal orienté, plus bas = pire).
    idea_hz = _signal(signals, ticker, "horizon")
    retained_hz = [s for s in (_signal(signals, t, "horizon") for t in retained) if s is not None]
    if idea_hz is not None and retained_hz and idea_hz < statistics.median(retained_hz):
        tensions.append(Tension(
            dimension="horizon",
            detail=(
                f"Pire période glissante sur {horizon_label} {idea_hz:.0f} %, sous la médiane "
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


# --- repères de risque du profil (P3) -----------------------------------------------------------
# RISK_LIMITS, SEVERE_RATIO et tolerance_level sont définis dans `engine.constraints` (règle de
# tolérance partagée avec le classement) et réexportés ici.


def verdict_from(tensions: tuple[Tension, ...] | list[Tension]) -> str:
    if any(t.severe for t in tensions):
        return "incohérent avec le profil"
    return "cohérent avec réserve" if tensions else "cohérent"


def limit_tensions(
    *,
    level: str,
    volatility: Optional[float],
    max_drawdown: Optional[float],
    volatility_evidence: Optional[str] = None,
    drawdown_evidence: Optional[str] = None,
    limit_evidence: Optional[dict[str, str]] = None,
    capped_class: bool = False,
) -> list[Tension]:
    """Tensions entre un titre et les repères de risque du profil (valeurs en points de %).

    Une tension est sévère (verdict « incohérent ») exactement quand la règle de tolérance du
    classement écarterait le titre (`engine.constraints.risk_breach`) : les deux écrans concordent.
    """
    max_vol, max_loss = RISK_LIMITS[level]
    limit_evidence = limit_evidence or {}
    breach = risk_breach(level, volatility, max_drawdown, capped_class=capped_class)
    tensions: list[Tension] = []
    if volatility is not None and volatility > max_vol:
        tensions.append(Tension(
            dimension="repère de volatilité",
            detail=(
                f"Volatilité annualisée de {pct_fr(volatility)} %, au-dessus du repère de {max_vol:.0f} % "
                f"retenu pour une tolérance au risque {level}."
            ),
            severe=breach.excluded,
            evidence_id=volatility_evidence,
            evidence_ids=tuple(i for i in (limit_evidence.get("volatilite"),) if i),
        ))
    if max_drawdown is not None and max_drawdown < max_loss:
        tensions.append(Tension(
            dimension="repère de perte maximale",
            detail=(
                f"Perte maximale observée de {pct_fr(abs(max_drawdown))} %, au-delà du repère de "
                f"{abs(max_loss):.0f} % retenu pour une tolérance au risque {level}."
            ),
            severe=breach.excluded,
            evidence_id=drawdown_evidence,
            evidence_ids=tuple(i for i in (limit_evidence.get("perte_max"),) if i),
        ))
    return tensions


def reference_medians(
    ticker: str, ranking_tickers: list[str], signals: dict[str, dict[str, Optional[float]]]
) -> dict[str, Optional[float]]:
    """Médianes de référence utilisées par `evaluate_idea` : volatilité et pire période de 3 ans
    des actifs classés pour le profil (hors le titre testé). Valeurs en points de %."""
    others = [t for t in ranking_tickers if t != ticker]
    stab = [s for s in (_signal(signals, t, "stabilite") for t in others) if s is not None]
    hz = [s for s in (_signal(signals, t, "horizon") for t in others) if s is not None]
    return {
        "volatilite": -statistics.median(stab) if stab else None,
        "horizon": statistics.median(hz) if hz else None,
    }
