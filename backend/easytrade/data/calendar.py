"""Calendriers par marché (TSX, US, crypto 7 j/7) et alignement explicite.

Conception : docs/04_DONNEES.md section 1
Règles :
- Aucun calendrier de jours fériés codé en dur : les séances d'un calendrier sont l'ensemble des
  dates où au moins un actif de ce calendrier a un prix.
- Les rendements sont calculés par actif, sur ses propres séances, avant toute jointure.
- Pour comparer deux actifs (corrélation), on ne garde que les dates où les deux ont un prix, puis
  on calcule les rendements sur ces dates communes (`align_prices`).
"""
from __future__ import annotations

import pandas as pd

from easytrade.config import (
    CRYPTO_ASSET_CLASS,
    CRYPTO_DAYS_PER_YEAR,
    TRADING_DAYS_PER_YEAR,
)

CAL_TSX = "TSX"
CAL_US = "US"
CAL_CRYPTO = "CRYPTO"


def annualization_factor(asset_class: str) -> int:
    """365 pour la crypto (jours civils UTC), 252 pour les actions et FNB."""
    return CRYPTO_DAYS_PER_YEAR if asset_class == CRYPTO_ASSET_CLASS else TRADING_DAYS_PER_YEAR


def calendar_of(asset_class: str, market: str) -> str:
    if asset_class == CRYPTO_ASSET_CLASS:
        return CAL_CRYPTO
    return CAL_TSX if market == "TSX" else CAL_US


def with_calendar(prices: pd.DataFrame) -> pd.DataFrame:
    out = prices.copy()
    out["calendar"] = [calendar_of(a, m) for a, m in zip(out["asset_class"], out["market"])]
    return out


def sessions(prices: pd.DataFrame, calendar_name: str) -> pd.DatetimeIndex:
    """Séances d'un calendrier : union des dates observées pour les actifs de ce calendrier."""
    p = prices if "calendar" in prices else with_calendar(prices)
    return pd.DatetimeIndex(sorted(p.loc[p["calendar"] == calendar_name, "date"].unique()))


def align_prices(prices: pd.DataFrame, tickers: list[str], column: str = "adj_close_cad") -> pd.DataFrame:
    """Prix en colonnes (un actif par colonne) sur les dates où **tous** les actifs ont un prix.

    Les dates où un des actifs est fermé sont retirées, sans remplissage. Les rendements
    calculés ensuite sur ce tableau couvrent donc le même intervalle pour tous les actifs.
    """
    wide = prices[prices["ticker"].isin(tickers)].pivot(index="date", columns="ticker", values=column)
    wide = wide.reindex(columns=tickers)
    return wide.dropna(how="any").sort_index()
