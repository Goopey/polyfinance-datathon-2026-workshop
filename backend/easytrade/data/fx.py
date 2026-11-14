"""Conversion CAD/USD, jours fériés, alignement de calendriers.

Conception : docs/04_DONNEES.md section 1
- Les agrégations sont en CAD ; un actif en USD est converti au taux USD/CAD du jour.
- La Banque du Canada ne publie pas de taux les jours fériés canadiens (et le week-end) :
  on reporte le dernier taux connu et on le signale (`fx_carried`, `fx_date`).
- On ne reporte jamais un taux futur (jointure strictement vers l'arrière).
"""
from __future__ import annotations

import pandas as pd

PRICE_COLUMNS_TO_CONVERT = ["close", "adj_close"]


class MissingFxError(ValueError):
    """Un prix en USD n'a aucun taux de change connu à sa date ou avant."""


class FxRates:
    def __init__(self, fx: pd.DataFrame):
        table = fx[["date", "usdcad"]].dropna().sort_values("date", kind="mergesort").reset_index(drop=True)
        if table["date"].duplicated().any():
            raise ValueError("Taux de change en double pour une même date")
        if (table["usdcad"] <= 0).any():
            raise ValueError("Taux de change nul ou négatif")
        self._table = table

    @property
    def first_date(self) -> pd.Timestamp:
        return self._table["date"].iloc[0]

    def rate_on(self, day) -> tuple[float, pd.Timestamp]:
        """Taux USD/CAD à la date donnée ou, à défaut, dernier taux connu. Retourne (taux, date du taux)."""
        day = pd.Timestamp(day)
        eligible = self._table[self._table["date"] <= day]
        if eligible.empty:
            raise MissingFxError(f"Aucun taux USD/CAD connu au {day.date()}")
        row = eligible.iloc[-1]
        return float(row["usdcad"]), row["date"]

    def attach_cad(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Ajoute `fx_rate`, `fx_date`, `fx_carried`, `close_cad`, `adj_close_cad`.

        Les prix en CAD gardent le taux 1. Les prix en USD utilisent le taux du jour ou le dernier
        connu. Les lignes retournées sont triées par (ticker, date).
        """
        fx = self._table.rename(columns={"date": "fx_date", "usdcad": "fx_rate"})
        left = prices.sort_values("date", kind="mergesort")
        merged = pd.merge_asof(left, fx, left_on="date", right_on="fx_date", direction="backward")

        is_cad = merged["currency"] == "CAD"
        unknown_currency = ~merged["currency"].isin(["CAD", "USD"])
        if unknown_currency.any():
            raise ValueError(f"Devises non gérées : {sorted(merged.loc[unknown_currency, 'currency'].unique())}")

        no_rate = (~is_cad) & merged["fx_rate"].isna()
        if no_rate.any():
            first = merged.loc[no_rate, "date"].min().date()
            raise MissingFxError(f"{int(no_rate.sum())} prix en USD sans taux de change connu (dès le {first})")

        merged.loc[is_cad, "fx_rate"] = 1.0
        merged.loc[is_cad, "fx_date"] = merged.loc[is_cad, "date"]
        merged["fx_carried"] = merged["fx_date"] != merged["date"]
        for column in PRICE_COLUMNS_TO_CONVERT:
            merged[f"{column}_cad"] = merged[column] * merged["fx_rate"]
        return merged.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
