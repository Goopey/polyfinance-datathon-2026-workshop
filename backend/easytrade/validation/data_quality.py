"""Contrôles qualité à l'ingestion → rapport `data/curated/quality_report.json`.

Conception : docs/04_DONNEES.md section 7
Les contrôles lisent les données via `PointInTimeStore`, à la date `as_of`. Le rapport est
déterministe : même entrée, même sortie (pas d'horodatage d'exécution).

Statuts : `pass` (rien à signaler), `warn` (à connaître, documenté), `fail` (à corriger avant usage).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from easytrade.config import QualityThresholds
from easytrade.data.calendar import sessions, with_calendar
from easytrade.data.point_in_time import DateLike, PointInTimeStore, to_timestamp

PRICE_FIELDS = ["open", "high", "low", "close", "adj_close"]
SAMPLE_SIZE = 10  # nombre maximal d'exemples listés par contrôle


def _day(value) -> str:
    return pd.Timestamp(value).date().isoformat()


def _check(check_id: str, title: str, status: str, count: int, details: Any = None, note: str = "") -> dict:
    return {"id": check_id, "title": title, "status": status, "count": int(count), "details": details or [], "note": note}


# --- anomalies d'opérations sur titres --------------------------------------------------------
def split_anomalies(actions: pd.DataFrame, min_ratio: float) -> pd.DataFrame:
    """Fractionnements au ratio invraisemblable (ex. 1,021 pour CNQ.TO au 2022-08-22).

    Un vrai fractionnement a un ratio d'au moins `min_ratio` (ou son inverse). Les lignes
    retournées ne sont **jamais** appliquées aux prix (ils sont déjà ajustés) : elles servent à
    avertir.
    """
    splits = actions[actions["action"] == "split"].copy()
    ratio = splits["value"].astype(float)
    effective = np.where(ratio >= 1.0, ratio, 1.0 / ratio)
    return splits[effective < min_ratio].reset_index(drop=True)


def anomaly_notes(actions: pd.DataFrame, min_ratio: float) -> dict[str, str]:
    """Mention de limite par ticker, à joindre aux preuves de ce ticker."""
    notes: dict[str, list[str]] = {}
    for row in split_anomalies(actions, min_ratio).itertuples():
        notes.setdefault(row.ticker, []).append(
            f"Anomalie de données : « fractionnement » de {row.value:g} le {_day(row.ex_date)}, probablement une "
            "distribution spéciale ; non appliqué, vérification auprès des relations investisseurs en attente."
        )
    return {ticker: " ".join(parts) for ticker, parts in sorted(notes.items())}


# --- contrôles ----------------------------------------------------------------------------
def _check_duplicates(prices: pd.DataFrame) -> dict:
    dup = prices[prices.duplicated(["date", "ticker"], keep=False)]
    sample = [{"date": _day(r.date), "ticker": r.ticker} for r in dup.head(SAMPLE_SIZE).itertuples()]
    return _check("duplicates", "Doublons (date, ticker)", "fail" if len(dup) else "pass", len(dup), sample)


def _check_nonpositive(prices: pd.DataFrame) -> dict:
    bad = prices[(prices[PRICE_FIELDS] <= 0).any(axis=1) | prices[PRICE_FIELDS].isna().any(axis=1)]
    sample = [{"date": _day(r.date), "ticker": r.ticker} for r in bad.head(SAMPLE_SIZE).itertuples()]
    return _check("nonpositive_prices", "Prix nuls, négatifs ou manquants", "fail" if len(bad) else "pass", len(bad), sample)


def _check_zero_volume(prices: pd.DataFrame) -> dict:
    zero = prices[prices["volume"] <= 0]
    sample = [{"date": _day(r.date), "ticker": r.ticker} for r in zero.head(SAMPLE_SIZE).itertuples()]
    return _check(
        "zero_volume", "Volumes nuls", "warn" if len(zero) else "pass", len(zero), sample,
        "Un volume nul n'invalide pas le prix mais indique une séance peu fiable.",
    )


def _missing_runs(missing_flags: np.ndarray) -> list[tuple[int, int]]:
    """Plages (début, longueur) de True consécutifs."""
    runs, start = [], None
    for i, flag in enumerate(missing_flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i - start))
            start = None
    if start is not None:
        runs.append((start, len(missing_flags) - start))
    return runs


def _check_gaps(prices: pd.DataFrame, max_gap: int) -> dict:
    """Séances du calendrier de l'actif absentes pour cet actif, par plages de plus de `max_gap`."""
    p = with_calendar(prices)
    calendars = {name: sessions(p, name) for name in p["calendar"].unique()}
    found = []
    for ticker, group in p.groupby("ticker", sort=True):
        cal = calendars[group["calendar"].iloc[0]]
        window = cal[(cal >= group["date"].min()) & (cal <= group["date"].max())]
        missing = ~window.isin(group["date"])
        for start, length in _missing_runs(np.asarray(missing)):
            if length > max_gap:
                found.append({"ticker": ticker, "from": _day(window[start]), "missing_sessions": length})
    return _check(
        "gaps", f"Trous de plus de {max_gap} séances", "warn" if found else "pass", len(found), found[:SAMPLE_SIZE],
        "Séances du calendrier = union des dates observées pour le même marché (TSX, US, crypto).",
    )


def _check_large_moves(prices: pd.DataFrame, actions: pd.DataFrame, threshold: float) -> dict:
    p = prices.sort_values(["ticker", "date"], kind="mergesort").copy()
    p["ret"] = p.groupby("ticker")["adj_close"].pct_change()
    big = p[p["ret"].abs() > threshold]
    action_keys = set(zip(actions["ticker"], actions["ex_date"]))
    rows = []
    for r in big.itertuples():
        rows.append({
            "ticker": r.ticker, "date": _day(r.date), "return": round(float(r.ret), 6),
            "explained_by_corporate_action": (r.ticker, r.date) in action_keys,
        })
    unexplained = [r for r in rows if not r["explained_by_corporate_action"]]
    return _check(
        "large_moves", f"Variations de plus de {threshold:.0%} sur une journée",
        "warn" if unexplained else "pass", len(rows), rows[:SAMPLE_SIZE],
        "Rapprochées des opérations sur titres à la même date ; une variation non expliquée est à vérifier.",
    )


def _check_fx_coverage(prices: pd.DataFrame) -> dict:
    usd = prices[prices["currency"] == "USD"]
    carried = usd[usd["fx_carried"]]
    max_carry = int((carried["date"] - carried["fx_date"]).dt.days.max()) if len(carried) else 0
    missing = int(usd["fx_rate"].isna().sum())
    details = {
        "usd_price_rows": int(len(usd)),
        "rows_with_carried_rate": int(len(carried)),
        "max_days_carried": max_carry,
        "rows_without_rate": missing,
    }
    return _check(
        "fx_coverage", "Couverture du change sur toutes les dates utilisées",
        "fail" if missing else "pass", missing, details,
        "Les jours sans taux (fériés canadiens, week-ends crypto) utilisent le dernier taux connu, jamais un taux futur.",
    )


def _check_min_observations(prices: pd.DataFrame, minimum: int) -> dict:
    counts = prices.groupby("ticker").size()
    short = [{"ticker": t, "observations": int(n)} for t, n in counts.items() if n < minimum]
    return _check("min_observations", f"Au moins {minimum} observations par actif", "fail" if short else "pass", len(short), short)


def _check_split_anomalies(actions: pd.DataFrame, min_ratio: float) -> dict:
    anomalies = split_anomalies(actions, min_ratio)
    details = []
    for r in anomalies.itertuples():
        details.append({
            "ticker": r.ticker, "ex_date": _day(r.ex_date), "ratio": float(r.value),
            "treatment": "Non appliqué (prix déjà ajustés). Mention ajoutée aux limites de chaque preuve de ce ticker.",
            "status": "à vérifier auprès des relations investisseurs",
            "max_relative_effect_on_prior_prices_pct": round((float(r.value) - 1.0) * 100.0, 3),
        })
    return _check(
        "split_anomalies", "Fractionnements au ratio invraisemblable", "warn" if details else "pass", len(details), details,
        "Si le facteur est erroné, les prix antérieurs à la date sont décalés d'au plus l'effet indiqué.",
    )


def build_quality_report(store: PointInTimeStore, as_of: DateLike, thresholds: QualityThresholds) -> dict:
    as_of_ts = to_timestamp(as_of)
    prices = store.prices(as_of_ts)
    actions = store.corporate_actions(as_of_ts)
    checks = [
        _check_duplicates(prices),
        _check_nonpositive(prices),
        _check_zero_volume(prices),
        _check_gaps(prices, thresholds.max_gap_sessions),
        _check_large_moves(prices, actions, thresholds.max_daily_move),
        _check_fx_coverage(prices),
        _check_min_observations(prices, thresholds.min_observations),
        _check_split_anomalies(actions, thresholds.min_split_ratio),
    ]
    summary = {status: sum(1 for c in checks if c["status"] == status) for status in ("pass", "warn", "fail")}
    return {
        "as_of": _day(as_of_ts),
        "tickers": int(prices["ticker"].nunique()),
        "price_rows": int(len(prices)),
        "thresholds": {
            "max_gap_sessions": thresholds.max_gap_sessions,
            "max_daily_move": thresholds.max_daily_move,
            "min_observations": thresholds.min_observations,
            "min_split_ratio": thresholds.min_split_ratio,
        },
        "summary": summary,
        "checks": checks,
    }


def write_quality_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
