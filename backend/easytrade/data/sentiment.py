"""Sentiment mensuel (data/reference/sentiment.csv) lu à une date d'analyse.

Conception : docs/04_DONNEES.md (section 11)
Deux mesures, issues de l'instantané `scripts/fetch_finnhub.py --only sentiment` :
- `analystes` : nombre de recommandations « achat fort / achat / conserver / vente / vente forte » du mois ;
- `inities`   : indice de sentiment des initiés (MSPR, de -100 à +100 ; actions américaines seulement).
Un mois n'est connu qu'une fois terminé (+ délai pour les initiés, config.py) : l'analyse ne lit que le
dernier mois publié à sa date. Affichage seulement : le sentiment n'entre ni dans le score ni dans la décision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from easytrade.config import SENTIMENT_ANALYST_LAG_DAYS, SENTIMENT_INSIDER_LAG_DAYS
from easytrade.data.point_in_time import DateLike, filter_published

FILENAME = "sentiment.csv"
COUNTS = ("strong_buy", "buy", "hold", "sell", "strong_sell")
LAGS = {"analystes": SENTIMENT_ANALYST_LAG_DAYS, "inities": SENTIMENT_INSIDER_LAG_DAYS}


@dataclass(frozen=True)
class AnalystMonth:
    ticker: str
    period: date
    published_at: date
    counts: dict[str, int]
    document_url: str
    retrieved_at: Optional[date]

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def balance(self) -> float:
        """(achats − ventes) ÷ total, dans [-1, 1] ; 0 sans recommandation."""
        if not self.total:
            return 0.0
        c = self.counts
        return (c["strong_buy"] + c["buy"] - c["sell"] - c["strong_sell"]) / self.total


@dataclass(frozen=True)
class InsiderMonth:
    ticker: str
    period: date
    published_at: date
    mspr: float
    change: Optional[float]
    document_url: str
    retrieved_at: Optional[date]


def load_sentiment(reference_dir: Path) -> pd.DataFrame:
    """Table typée ; `published_at` = fin du mois (+ délai). Fichier absent : table vide."""
    path = Path(reference_dir) / FILENAME
    if not path.exists():
        return pd.DataFrame(columns=["ticker", "kind", "period", "published_at"])
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    table["period"] = pd.to_datetime(table["period"], errors="coerce")
    month_end = table["period"] + pd.offsets.MonthEnd(0)
    table["published_at"] = month_end + pd.to_timedelta(table["kind"].map(LAGS).fillna(0), unit="D")
    table["retrieved_at"] = pd.to_datetime(table["retrieved_at"], errors="coerce")
    return table.dropna(subset=["period"]).reset_index(drop=True)


def _number(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def latest_sentiment(table: pd.DataFrame, ticker: str,
                     as_of: DateLike) -> tuple[Optional[AnalystMonth], Optional[InsiderMonth]]:
    """Dernier mois publié à `as_of`, pour les analystes et pour les initiés."""
    known = filter_published(table[table["ticker"] == ticker], as_of) if len(table) else table
    analysts = insiders = None
    rows = known[known["kind"] == "analystes"].sort_values("period", kind="mergesort")
    if len(rows):
        r = rows.iloc[-1]
        analysts = AnalystMonth(
            ticker=ticker, period=r["period"].date(), published_at=r["published_at"].date(),
            counts={k: int(_number(r[k]) or 0) for k in COUNTS}, document_url=str(r["document_url"]),
            retrieved_at=None if pd.isna(r["retrieved_at"]) else r["retrieved_at"].date(),
        )
    rows = known[known["kind"] == "inities"].sort_values("period", kind="mergesort")
    if len(rows) and _number(rows.iloc[-1]["mspr"]) is not None:
        r = rows.iloc[-1]
        insiders = InsiderMonth(
            ticker=ticker, period=r["period"].date(), published_at=r["published_at"].date(),
            mspr=float(r["mspr"]), change=_number(r["change"]), document_url=str(r["document_url"]),
            retrieved_at=None if pd.isna(r["retrieved_at"]) else r["retrieved_at"].date(),
        )
    return analysts, insiders


# Libellé affiché (hypothèses de l'équipe) : les analystes penchent en moyenne vers l'achat, d'où un
# seuil « positif » élevé ; l'indice des initiés sert seulement quand aucun analyste ne suit le titre.
ANALYST_POSITIVE, ANALYST_NEGATIVE = 0.5, 0.1
INSIDER_POSITIVE, INSIDER_NEGATIVE = 25.0, -25.0


def sentiment_label(analysts: Optional[AnalystMonth], insiders: Optional[InsiderMonth]) -> str:
    if analysts is not None and analysts.total:
        if analysts.balance >= ANALYST_POSITIVE:
            return "positif"
        return "négatif" if analysts.balance < ANALYST_NEGATIVE else "neutre"
    if insiders is not None:
        if insiders.mspr >= INSIDER_POSITIVE:
            return "positif"
        return "négatif" if insiders.mspr <= INSIDER_NEGATIVE else "neutre"
    return "neutre"
