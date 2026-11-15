"""Critère « qualité » des actions : rentabilité, endettement comparé au secteur, marge.

Conception : docs/03_DECISION_ENGINE.md (section « Qualité »)
Méthode (hypothèse de l'équipe, décidée le 2026-11-15) :
- rentabilité des fonds propres (ROE) : rang centile parmi toutes les actions de l'univers ;
- endettement (dette / fonds propres, plus bas = mieux) : rang centile **dans le secteur seulement**,
  car une banque emprunte par nature (RY ≈ 2,6 contre AAPL ≈ 0,7) ; composante omise si le secteur
  compte moins de deux actions avec une valeur ;
- marge nette : rang centile parmi les actions qui en ont une (absente pour les banques) ;
- score = moyenne des composantes disponibles, dans [0, 1].
FNB et crypto : critère « non applicable » (pas de comptes de société), voir `signals.applicable`.
Python déterministe ; seules les valeurs publiées à la date d'analyse sont lues (data/fundamentals.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from easytrade.data.fundamentals import FundamentalPoint
from easytrade.engine.scoring import percentile_rank
from easytrade.engine.signals import applicable

ROE, LEVERAGE, MARGIN = "roe", "totalDebtToEquity", "netMargin"
MIN_SECTOR_PEERS = 2


@dataclass(frozen=True)
class QualityScore:
    ticker: str
    sector: str
    score: float                              # moyenne des rangs disponibles, dans [0, 1]
    roe: Optional[FundamentalPoint]
    leverage: Optional[FundamentalPoint]
    margin: Optional[FundamentalPoint]
    leverage_position: Optional[int]          # 1 = le moins endetté du secteur
    sector_peers: int                         # actions du secteur avec une valeur d'endettement
    components: tuple[str, ...]               # composantes réellement utilisées


def quality_scores(assets: pd.DataFrame, known: dict[str, dict[str, FundamentalPoint]]) -> dict[str, QualityScore]:
    """Score de qualité des actions qui ont au moins une composante connue à la date d'analyse."""
    rows = [(str(r["ticker"]), str(r["sector"])) for _, r in assets.iterrows()
            if applicable("qualite", str(r["asset_class"]))]

    def values(metric: str) -> dict[str, float]:
        return {t: known[t][metric].value for t, _ in rows if metric in known.get(t, {})}

    roe_rank = percentile_rank(values(ROE))
    margin_rank = percentile_rank(values(MARGIN))
    leverage = values(LEVERAGE)
    leverage_rank: dict[str, float] = {}
    position: dict[str, tuple[int, int]] = {}
    for sector in sorted({s for _, s in rows}):
        group = {t: v for t, v in leverage.items() if (t, sector) in rows}
        if len(group) < MIN_SECTOR_PEERS:
            continue
        ranks = percentile_rank({t: -v for t, v in group.items()})  # moins endetté = mieux
        for ticker, value in group.items():
            leverage_rank[ticker] = ranks[ticker]
            position[ticker] = (1 + sum(1 for u in group.values() if u < value), len(group))

    out: dict[str, QualityScore] = {}
    for ticker, sector in rows:
        parts = {name: rank for name, rank in (
            (ROE, roe_rank.get(ticker)), (LEVERAGE, leverage_rank.get(ticker)), (MARGIN, margin_rank.get(ticker)),
        ) if rank is not None}
        if not parts:
            continue
        facts = known.get(ticker, {})
        place, peers = position.get(ticker, (None, 0))
        out[ticker] = QualityScore(
            ticker=ticker, sector=sector, score=sum(parts.values()) / len(parts),
            roe=facts.get(ROE), leverage=facts.get(LEVERAGE), margin=facts.get(MARGIN),
            leverage_position=place, sector_peers=peers, components=tuple(parts),
        )
    return out
