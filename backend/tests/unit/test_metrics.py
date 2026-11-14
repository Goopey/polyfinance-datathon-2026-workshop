"""Indicateurs déterministes recoupés par calcul indépendant.
Conception : docs/02_AGENTS.md
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.validation import risk
from easytrade.validation.metrics import (
    annualized_return,
    annualized_volatility,
    compute_metrics_table,
    correlation_metric,
    period_return,
)


def _series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_rendement_annualise():
    s = _series([100, 110, 121])  # +10 % par période, deux rendements
    assert annualized_return(s, 2) == pytest.approx(0.21)
    assert annualized_return(s, 4) == pytest.approx(1.1**4 - 1)
    assert annualized_return(_series([100]), 252) is None


def test_volatilite_annualisee():
    s = _series([100, 110, 99, 108.9])  # rendements : +10 %, -10 %, +10 %
    r = np.array([0.1, -0.1, 0.1])
    assert annualized_volatility(s, 252) == pytest.approx(r.std(ddof=1) * np.sqrt(252))
    assert annualized_volatility(_series([100, 101]), 252) is None


def test_perte_maximale():
    assert risk.max_drawdown(_series([100, 120, 90, 130, 104])) == pytest.approx(-0.25)
    assert risk.max_drawdown(_series([100, 101, 102])) == 0.0
    assert risk.max_drawdown(_series([100])) is None


def test_pire_periode_glissante():
    s = _series([100, 110, 80, 90, 120])
    value, start, end = risk.worst_rolling_return(s, 2)
    assert value == pytest.approx(80 / 100 - 1)
    assert (start, end) == (s.index[0], s.index[2])
    assert risk.worst_rolling_return(s, 5) is None


def test_rendement_de_periode():
    s = pd.Series([100.0, 105.0, 90.0, 99.0], index=pd.to_datetime(["2021-12-30", "2021-12-31", "2022-06-30", "2022-12-30"]))
    assert period_return(s, pd.Timestamp("2021-12-31"), pd.Timestamp("2022-12-31")) == pytest.approx(99 / 105 - 1)
    assert period_return(s, pd.Timestamp("2021-12-01"), pd.Timestamp("2021-12-20")) is None


def test_correlation_sur_dates_communes():
    idx = pd.bdate_range("2024-01-01", periods=10)
    a = pd.Series(np.linspace(100, 110, 10) + [0, 1, 0, 1, 0, 1, 0, 1, 0, 1], index=idx)
    b = a * 2
    value, n = risk.correlation(a, b, min_common=5)
    assert value == pytest.approx(1.0) and n == 9
    assert risk.correlation(a, b, min_common=50) is None


def test_table_des_indicateurs_et_preuves(store, registry, settings):
    ledger = EvidenceLedger(settings.as_of)
    table = compute_metrics_table(store, settings.as_of, ledger, registry, settings.quality, tickers=["AAPL", "CNQ.TO"])
    assert set(table["ticker"]) == {"AAPL", "CNQ.TO"}
    computed = table[table["value"].notna()]
    assert computed["evidence_id"].notna().all() and set(computed["evidence_id"]) == set(ledger.ids())
    assert table.loc[table["value"].isna(), "evidence_id"].isna().all()
    for evidence in ledger:
        assert evidence.published_at <= settings.as_of and evidence.retrieved_at is not None
        assert evidence.value is not None and evidence.source.source_id == "starter_prices"
        if evidence.subject == "CNQ.TO":
            assert "2022-08-22" in evidence.limits
        else:
            assert "2022-08-22" not in evidence.limits


def test_donnees_insuffisantes_sans_preuve(store, registry):
    as_of = "2021-12-31"  # une quarantaine de séances seulement
    ledger = EvidenceLedger(date(2021, 12, 31))
    table = compute_metrics_table(store, as_of, ledger, registry, tickers=["SPY"])
    row = table[(table["metric"] == "worst_rolling_3y")].iloc[0]
    assert row["value"] is None or pd.isna(row["value"])
    assert row["note"] and pd.isna(row["evidence_id"])


def test_as_of_du_registre_doit_correspondre(store, registry):
    with pytest.raises(ValueError):
        compute_metrics_table(store, "2024-01-31", EvidenceLedger(date(2024, 2, 29)), registry, tickers=["SPY"])


def test_correlation_avec_preuve(store, registry, settings):
    ledger = EvidenceLedger(settings.as_of)
    result = correlation_metric(store, settings.as_of, ledger, registry, "SPY", "QQQ", settings.quality)
    assert 0.8 < result.value <= 1.0 and result.evidence_id in ledger
