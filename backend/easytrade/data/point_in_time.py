"""Filtre point-in-time : ne renvoie que les données avec published_at <= as_of.

Conception : docs/04_DONNEES.md section 4
Point d'accès unique aux données pour les modules d'analyse : aucun ne lit les fichiers directement.
- Prix, change, opérations sur titres : publiés à leur date.
- Macro : date de publication = date d'observation + délai prudent (config.py, hypothèse).
  Une série inconnue est refusée plutôt que supposée publiée le jour même.
- Fondamentaux (à venir) : date de dépôt, via la même fonction `filter_published`.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Optional, Union

import pandas as pd

from easytrade.config import MACRO_DAILY_LAG_DAYS, MACRO_PUBLICATION_LAG, Settings
from easytrade.data.fx import FxRates
from easytrade.data.loaders import StarterData, load_starter

DateLike = Union[str, date, pd.Timestamp]


def to_timestamp(value: DateLike) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def macro_published_at(series_id: str, observed_at: pd.Series) -> pd.Series:
    """Date de publication des observations d'une série macro (délai prudent, voir config.py)."""
    if series_id in MACRO_PUBLICATION_LAG:
        months, days = MACRO_PUBLICATION_LAG[series_id]
        return observed_at + pd.DateOffset(months=months, days=days)
    if series_id in MACRO_DAILY_LAG_DAYS:
        return observed_at + pd.Timedelta(days=MACRO_DAILY_LAG_DAYS[series_id])
    raise KeyError(f"Délai de publication inconnu pour la série macro {series_id} (à ajouter dans config.py)")


def filter_published(df: pd.DataFrame, as_of: DateLike, column: str = "published_at") -> pd.DataFrame:
    """Lignes dont la date de publication est <= as_of."""
    return df[df[column] <= to_timestamp(as_of)]


class PointInTimeStore:
    def __init__(self, data: StarterData):
        self._assets = data.assets
        self._fx = data.fx
        self._actions = data.corporate_actions
        self._fx_rates = FxRates(data.fx)
        # Convertir tout l'historique d'un coup est sûr : la ligne du jour d utilise un taux <= d.
        self._prices = self._fx_rates.attach_cad(data.prices)
        self._macro = self._with_publication_dates(data.macro)

    @classmethod
    def from_settings(cls, settings: Settings) -> "PointInTimeStore":
        return cls(load_starter(settings.starter_dir))

    @staticmethod
    def _with_publication_dates(macro: pd.DataFrame) -> pd.DataFrame:
        parts = []
        for series_id, group in macro.groupby("series_id", sort=True):
            group = group.copy()
            group["published_at"] = macro_published_at(series_id, group["observed_at"])
            parts.append(group)
        out = pd.concat(parts, ignore_index=True)
        return out.sort_values(["series_id", "observed_at"], kind="mergesort").reset_index(drop=True)

    # --- accès filtrés -------------------------------------------------------------------
    def assets(self) -> pd.DataFrame:
        return self._assets.copy()

    def prices(self, as_of: DateLike, tickers: Optional[Iterable[str]] = None) -> pd.DataFrame:
        out = filter_published(self._prices, as_of)
        if tickers is not None:
            out = out[out["ticker"].isin(list(tickers))]
        return out.reset_index(drop=True)

    def fx(self, as_of: DateLike) -> pd.DataFrame:
        return filter_published(self._fx, as_of).reset_index(drop=True)

    def corporate_actions(self, as_of: DateLike, tickers: Optional[Iterable[str]] = None) -> pd.DataFrame:
        out = filter_published(self._actions, as_of)
        if tickers is not None:
            out = out[out["ticker"].isin(list(tickers))]
        return out.reset_index(drop=True)

    def macro(self, as_of: DateLike, series_ids: Optional[Iterable[str]] = None) -> pd.DataFrame:
        out = filter_published(self._macro, as_of)
        if series_ids is not None:
            out = out[out["series_id"].isin(list(series_ids))]
        return out.reset_index(drop=True)

    def macro_latest(self, as_of: DateLike, series_id: str) -> Optional[pd.Series]:
        """Dernière valeur de la série **publiée** à `as_of` (pas la dernière observée)."""
        rows = self.macro(as_of, [series_id])
        if rows.empty:
            return None
        return rows.sort_values(["published_at", "observed_at"], kind="mergesort").iloc[-1]
