"""Chargement du jeu de départ (data/raw/starter) en tables typées.

Conception : docs/04_DONNEES.md sections 1, 4 et 5
Chaque enregistrement porte `observed_at`, `retrieved_at` et, quand elle ne dépend pas d'un délai
à appliquer, `published_at`. Les séries macro reçoivent `published_at` dans `point_in_time`.
Ce module ne filtre pas dans le temps : l'accès aux données passe par `PointInTimeStore`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]


@dataclass(frozen=True)
class StarterData:
    assets: pd.DataFrame
    prices: pd.DataFrame
    corporate_actions: pd.DataFrame
    fx: pd.DataFrame
    macro: pd.DataFrame


def _retrieved_on(starter_dir: Path) -> dict[str, pd.Timestamp]:
    meta = pd.read_csv(starter_dir / "sources_metadata.csv")
    meta["retrieved_on"] = pd.to_datetime(meta["retrieved_on"], errors="coerce")
    return dict(zip(meta["file"], meta["retrieved_on"]))


def load_reference_table(reference_dir: Path, filename: str, date_column: str) -> pd.DataFrame:
    """Table de référence saisie à la main (`esg_evidence.csv`, `graph_edges.csv`), typée.

    `published_at` = date du document (`date_column`) : l'accès passe ensuite par
    `filter_published`, comme pour toute autre donnée. Un fichier réduit à son en-tête donne
    une table vide (aucune preuve saisie), pas une erreur.
    """
    table = pd.read_csv(reference_dir / filename, dtype=str, keep_default_na=False)
    table["published_at"] = pd.to_datetime(table[date_column], errors="coerce")
    table["observed_at"] = table["published_at"]
    return table


def load_starter(starter_dir: Path) -> StarterData:
    """Lit les six fichiers du jeu de départ. Lève une erreur si un fichier ou une colonne manque."""
    retrieved = _retrieved_on(starter_dir)

    assets = pd.read_csv(starter_dir / "assets_universe.csv", dtype=str)

    prices = pd.read_csv(starter_dir / "prices_daily.csv", parse_dates=["date"])
    prices = prices.merge(assets[["ticker", "asset_class", "market"]], on="ticker", how="left", validate="m:1")
    if prices["asset_class"].isna().any():
        missing = sorted(prices.loc[prices["asset_class"].isna(), "ticker"].unique())
        raise ValueError(f"Tickers absents de l'univers : {missing}")
    prices["observed_at"] = prices["date"]
    prices["published_at"] = prices["date"]  # prix : date de clôture
    prices["retrieved_at"] = retrieved["prices_daily.csv"]
    prices = prices.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    actions = pd.read_csv(starter_dir / "corporate_actions.csv", parse_dates=["ex_date"])
    actions["observed_at"] = actions["ex_date"]
    actions["published_at"] = actions["ex_date"]
    actions["retrieved_at"] = retrieved["corporate_actions.csv"]
    actions = actions.sort_values(["ticker", "ex_date", "action"], kind="mergesort").reset_index(drop=True)

    fx = pd.read_csv(starter_dir / "fx_usdcad_daily.csv", parse_dates=["date"])
    fx["observed_at"] = fx["date"]
    fx["published_at"] = fx["date"]  # taux du jour publié le jour même
    fx["retrieved_at"] = retrieved["fx_usdcad_daily.csv"]
    fx = fx.sort_values("date", kind="mergesort").reset_index(drop=True)

    macro = pd.read_csv(starter_dir / "macro_rates.csv", parse_dates=["date"])
    macro["observed_at"] = macro["date"]
    macro["retrieved_at"] = retrieved["macro_rates.csv"]
    macro = macro.sort_values(["series_id", "date"], kind="mergesort").reset_index(drop=True)

    return StarterData(assets=assets, prices=prices, corporate_actions=actions, fx=fx, macro=macro)
