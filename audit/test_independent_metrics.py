"""Audit — recalcul indépendant des indicateurs financiers.

Aucun code du backend n'est utilisé pour le calcul de référence : lecture CSV, conversion USD→CAD,
rendements, volatilité, perte maximale et pire période glissante sont réécrits ici avec la
bibliothèque standard (csv, math, statistics). Les valeurs du backend
(`easytrade.validation.metrics.compute_metrics_table`) sont ensuite comparées à ces références.

Lancer : backend/.venv/Scripts/python.exe -m pytest audit -q -p no:cacheprovider
"""
from __future__ import annotations

import bisect
import csv
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "data" / "raw" / "starter"
AS_OF = date(2026, 11, 12)
TOL = 1e-6  # tolérance relative


# ---------- référence indépendante ----------------------------------------------------------------

def _load():
    assets = {r["ticker"]: r for r in csv.DictReader(open(STARTER / "assets_universe.csv", encoding="utf-8"))}
    fx_rows = sorted((date.fromisoformat(r["date"]), float(r["usdcad"]))
                     for r in csv.DictReader(open(STARTER / "fx_usdcad_daily.csv", encoding="utf-8")) if r["usdcad"])
    fx_dates = [d for d, _ in fx_rows]
    prices = defaultdict(list)
    for r in csv.DictReader(open(STARTER / "prices_daily.csv", encoding="utf-8")):
        d = date.fromisoformat(r["date"])
        if d > AS_OF or not r["adj_close"]:
            continue
        px = float(r["adj_close"])
        if r["currency"] == "USD":
            i = bisect.bisect_right(fx_dates, d) - 1  # dernier taux connu, jamais un taux futur
            assert i >= 0, f"pas de taux pour {d}"
            px *= fx_rows[i][1]
        prices[r["ticker"]].append((d, px))
    for t in prices:
        prices[t].sort()
    return assets, prices


ASSETS, PRICES = _load()


def ppy(ticker: str) -> int:
    return 365 if ASSETS[ticker]["asset_class"] == "crypto" else 252


def ref_annualized_return(p, n_per_year):
    return (p[-1] / p[0]) ** (n_per_year / (len(p) - 1)) - 1


def ref_volatility(p, n_per_year):
    r = [p[i] / p[i - 1] - 1 for i in range(1, len(p))]
    return statistics.stdev(r) * math.sqrt(n_per_year)


def ref_max_drawdown(p):
    peak, worst = p[0], 0.0
    for x in p:
        peak = max(peak, x)
        worst = min(worst, x / peak - 1)
    return worst


def ref_worst_rolling(p, k):
    return min(p[i + k] / p[i] - 1 for i in range(len(p) - k))


def ref_return_2022(series):
    base = [x for d, x in series if d <= date(2021, 12, 31)][-1]
    end = [x for d, x in series if d <= date(2022, 12, 31)][-1]
    return end / base - 1


# ---------- valeurs du backend ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def backend_table():
    from easytrade.explain.evidence_ledger import EvidenceLedger
    from easytrade.orchestration.pipeline import Workspace
    from easytrade.validation.metrics import compute_metrics_table

    ws = Workspace.load()
    ledger = EvidenceLedger(AS_OF)
    table = compute_metrics_table(ws.store, AS_OF, ledger, ws.registry, ws.settings.quality)
    return {(r.ticker, r.metric, r.window): r.value for r in table.itertuples() if r.value is not None}


def _close(a, b):
    return math.isclose(a, b, rel_tol=TOL, abs_tol=1e-9)


@pytest.mark.parametrize("ticker", sorted(ASSETS))
def test_indicateurs_recalcules(ticker, backend_table):
    series = PRICES[ticker]
    p = [x for _, x in series]
    n = ppy(ticker)
    expected = {
        ("annualized_return", "full"): ref_annualized_return(p, n) * 100,
        ("annualized_volatility", "full"): ref_volatility(p, n) * 100,
        ("max_drawdown", "full"): ref_max_drawdown(p) * 100,
        ("worst_rolling_3y", "full"): ref_worst_rolling(p, round(3 * n)) * 100,
        ("worst_rolling_1y", "full"): ref_worst_rolling(p, n) * 100,
        ("return_2022", "2022"): ref_return_2022(series) * 100,
    }
    mismatches = []
    for (metric, window), want in expected.items():
        got = backend_table.get((ticker, metric, window))
        if got is None or not _close(got, want):
            mismatches.append(f"{metric}/{window}: backend={got} référence={want}")
    assert not mismatches, f"{ticker} : " + " ; ".join(mismatches)


# ---------- exemples analytiques (formules du backend sur des séries connues) ----------------------

def test_exemples_analytiques():
    import pandas as pd
    from easytrade.validation.metrics import annualized_return, annualized_volatility
    from easytrade.validation.risk import max_drawdown, worst_rolling_return

    idx = pd.date_range("2024-01-01", periods=253, freq="B")
    growth = pd.Series([100 * 1.10 ** (i / 252) for i in range(253)], index=idx)  # +10 %/an exactement
    assert math.isclose(annualized_return(growth, 252), 0.10, rel_tol=1e-12)
    assert annualized_volatility(growth, 252) < 1e-12  # croissance régulière : volatilité nulle
    alt = pd.Series([100, 110, 99, 108.9, 98.01], index=idx[:5])  # +10 %, -10 %, +10 %, -10 %
    sd = statistics.stdev([0.1, -0.1, 0.1, -0.1])
    assert math.isclose(annualized_volatility(alt, 252), sd * math.sqrt(252), rel_tol=1e-12)
    dd = pd.Series([100, 120, 60, 90, 130, 65], index=idx[:6])
    assert math.isclose(max_drawdown(dd), -0.5, rel_tol=1e-12)  # 120→60 et 130→65 : -50 %
    worst = worst_rolling_return(pd.Series([100, 50, 75, 150], index=idx[:4]), 2)
    assert math.isclose(worst[0], -0.25, rel_tol=1e-12)  # 100→75


# ---------- point-in-time : un calcul à une date passée n'utilise rien d'ultérieur ----------------

@pytest.mark.parametrize("as_of", [date(2023, 6, 30), date(2024, 12, 31)])
def test_aucune_donnee_posterieure(as_of):
    from easytrade.explain.evidence_ledger import EvidenceLedger
    from easytrade.orchestration.pipeline import Workspace
    from easytrade.validation.metrics import compute_metrics_table

    ws = Workspace.load()
    ledger = EvidenceLedger(as_of)
    table = compute_metrics_table(ws.store, as_of, ledger, ws.registry, ws.settings.quality)
    ends = [r.end for r in table.itertuples() if r.end is not None]
    assert ends and max(ends) <= as_of
    for ev in ledger:
        assert ev.published_at <= as_of, ev.evidence_id
    # Le rendement annualisé « toute la période » à as_of doit égaler la référence tronquée à as_of.
    series = [(d, x) for d, x in PRICES["SPY"] if d <= as_of]
    p = [x for _, x in series]
    got = {(r.ticker, r.metric, r.window): r.value for r in table.itertuples()}[("SPY", "annualized_return", "full")]
    assert _close(got, ref_annualized_return(p, 252) * 100)
