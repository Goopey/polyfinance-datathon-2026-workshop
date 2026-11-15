"""Fondamentaux annuels (data/reference/fundamentals.csv) lus à une date d'analyse.

Conception : docs/04_DONNEES.md (section 10), docs/03_DECISION_ENGINE.md (critère `qualite`)
Le fichier vient de l'instantané `scripts/fetch_finnhub.py` et porte la date de fin de chaque exercice.
Date de publication supposée = fin d'exercice + `FUNDAMENTALS_ANNUAL_LAG_DAYS` (hypothèse prudente,
config.py) : à la date d'analyse, on ne lit que l'exercice le plus récent qui était déjà public.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from easytrade.config import FUNDAMENTALS_ANNUAL_LAG_DAYS
from easytrade.data.point_in_time import DateLike, filter_published

FILENAME = "fundamentals.csv"


@dataclass(frozen=True)
class FundamentalPoint:
    ticker: str
    metric: str
    value: float
    period_end: date
    published_at: date
    source_id: str
    document_url: str
    retrieved_at: Optional[date]


def load_fundamentals(reference_dir: Path) -> pd.DataFrame:
    """Table typée ; `published_at` calculée. Fichier absent : table vide (critère non sourcé)."""
    path = Path(reference_dir) / FILENAME
    if not path.exists():
        return pd.DataFrame(columns=["ticker", "metric", "value", "period_end", "published_at", "source_id",
                                     "document_url", "retrieved_at"])
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    table["value"] = pd.to_numeric(table["value"], errors="coerce")
    table["period_end"] = pd.to_datetime(table["period_end"], errors="coerce")
    table["published_at"] = table["period_end"] + pd.Timedelta(days=FUNDAMENTALS_ANNUAL_LAG_DAYS)
    table["retrieved_at"] = pd.to_datetime(table["retrieved_at"], errors="coerce")
    return table.dropna(subset=["value", "period_end"]).reset_index(drop=True)


def latest_known(table: pd.DataFrame, as_of: DateLike) -> dict[str, dict[str, FundamentalPoint]]:
    """Par titre puis par indicateur : le dernier exercice publié au plus tard à `as_of`."""
    known = filter_published(table, as_of)
    out: dict[str, dict[str, FundamentalPoint]] = {}
    for (ticker, metric), group in known.groupby(["ticker", "metric"], sort=True):
        row = group.sort_values("period_end", kind="mergesort").iloc[-1]
        retrieved = row["retrieved_at"]
        out.setdefault(str(ticker), {})[str(metric)] = FundamentalPoint(
            ticker=str(ticker), metric=str(metric), value=float(row["value"]),
            period_end=row["period_end"].date(), published_at=row["published_at"].date(),
            source_id=str(row["source_id"]), document_url=str(row["document_url"]),
            retrieved_at=None if pd.isna(retrieved) else retrieved.date(),
        )
    return out
