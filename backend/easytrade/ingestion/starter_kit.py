"""Jeu de départ → tables préparées (prix, rendements, change, macro, indicateurs, preuves, qualité).

Conception : docs/04_DONNEES.md sections 5 et 7
Écrit dans `data/curated/` (non versionné, régénérable) :
`prices.parquet`, `returns.parquet`, `fx.parquet`, `macro.parquet`, `metrics.parquet`,
`evidence.jsonl`, `quality_report.json`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from easytrade.config import Settings, load_settings
from easytrade.data.calendar import with_calendar
from easytrade.data.point_in_time import PointInTimeStore
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.validation.data_quality import build_quality_report, write_quality_report
from easytrade.validation.metrics import compute_metrics_table

PRICE_COLUMNS = [
    "date", "ticker", "asset_class", "market", "calendar", "currency", "open", "high", "low", "close", "adj_close",
    "volume", "fx_rate", "fx_date", "fx_carried", "close_cad", "adj_close_cad",
    "observed_at", "published_at", "retrieved_at",
]


@dataclass(frozen=True)
class CuratedOutputs:
    paths: dict[str, Path]
    quality_summary: dict[str, int]
    evidence_count: int


def build_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Rendements quotidiens simples **par actif**, sur adj_close, avant toute jointure entre actifs."""
    p = prices.sort_values(["ticker", "date"], kind="mergesort")
    grouped = p.groupby("ticker", sort=True)
    out = p[["date", "ticker", "calendar"]].copy()
    out["ret_local"] = grouped["adj_close"].pct_change()
    out["ret_cad"] = grouped["adj_close_cad"].pct_change()
    return out.dropna(subset=["ret_local"]).reset_index(drop=True)


def build_curated(settings: Settings | None = None) -> CuratedOutputs:
    settings = settings or load_settings()
    as_of = pd.Timestamp(settings.as_of)
    out_dir = settings.curated_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    store = PointInTimeStore.from_settings(settings)
    registry = SourcesRegistry.load(settings.reference_dir)
    ledger = EvidenceLedger(settings.as_of)

    prices = with_calendar(store.prices(as_of))[PRICE_COLUMNS]
    returns = build_returns(prices)
    metrics = compute_metrics_table(store, as_of, ledger, registry, settings.quality)
    report = build_quality_report(store, as_of, settings.quality)

    paths = {
        "prices": out_dir / "prices.parquet",
        "returns": out_dir / "returns.parquet",
        "fx": out_dir / "fx.parquet",
        "macro": out_dir / "macro.parquet",
        "metrics": out_dir / "metrics.parquet",
        "evidence": out_dir / "evidence.jsonl",
        "quality_report": out_dir / "quality_report.json",
    }
    prices.to_parquet(paths["prices"], index=False)
    returns.to_parquet(paths["returns"], index=False)
    store.fx(as_of).to_parquet(paths["fx"], index=False)
    store.macro(as_of).to_parquet(paths["macro"], index=False)
    metrics.to_parquet(paths["metrics"], index=False)
    with open(paths["evidence"], "w", encoding="utf-8") as f:
        for record in ledger.to_records():
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_quality_report(report, paths["quality_report"])
    return CuratedOutputs(paths=paths, quality_summary=report["summary"], evidence_count=len(ledger))
