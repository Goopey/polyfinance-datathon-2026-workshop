"""Conversion CAD/USD, jours fériés, alignement de calendriers.
Conception : docs/04_DONNEES.md
"""
import pandas as pd
import pytest

from easytrade.data.calendar import (
    CAL_CRYPTO,
    CAL_TSX,
    CAL_US,
    align_prices,
    annualization_factor,
    calendar_of,
    sessions,
    with_calendar,
)
from easytrade.data.fx import FxRates, MissingFxError


def _fx():
    return pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"]), "usdcad": [1.30, 1.40, 1.50]})


def _prices(rows):
    df = pd.DataFrame(rows, columns=["date", "ticker", "currency", "close", "adj_close"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_taux_du_jour_et_dernier_taux_connu():
    fx = FxRates(_fx())
    assert fx.rate_on("2024-01-03") == (1.40, pd.Timestamp("2024-01-03"))
    assert fx.rate_on("2024-01-04") == (1.40, pd.Timestamp("2024-01-03"))  # jour sans taux : report
    with pytest.raises(MissingFxError):
        fx.rate_on("2024-01-01")


def test_conversion_cad_signale_les_reports():
    prices = _prices([
        ("2024-01-03", "AAA", "USD", 10.0, 10.0),
        ("2024-01-04", "AAA", "USD", 10.0, 10.0),  # pas de taux ce jour-là
        ("2024-01-04", "BBB.TO", "CAD", 20.0, 20.0),
    ])
    out = FxRates(_fx()).attach_cad(prices).set_index(["ticker", "date"])
    jour = out.loc[("AAA", pd.Timestamp("2024-01-03"))]
    assert jour["adj_close_cad"] == pytest.approx(14.0) and not jour["fx_carried"]
    report = out.loc[("AAA", pd.Timestamp("2024-01-04"))]
    assert report["adj_close_cad"] == pytest.approx(14.0) and report["fx_carried"]
    assert report["fx_date"] == pd.Timestamp("2024-01-03")
    cad = out.loc[("BBB.TO", pd.Timestamp("2024-01-04"))]
    assert cad["adj_close_cad"] == 20.0 and cad["fx_rate"] == 1.0 and not cad["fx_carried"]


def test_jamais_de_taux_futur():
    prices = _prices([("2024-01-01", "AAA", "USD", 10.0, 10.0)])
    with pytest.raises(MissingFxError):
        FxRates(_fx()).attach_cad(prices)


def test_devise_inconnue_refusee():
    prices = _prices([("2024-01-03", "AAA", "EUR", 10.0, 10.0)])
    with pytest.raises(ValueError):
        FxRates(_fx()).attach_cad(prices)


def test_annualisation_et_calendriers():
    assert annualization_factor("crypto") == 365
    assert annualization_factor("equity") == annualization_factor("etf_bond") == 252
    assert calendar_of("crypto", "Crypto (24/7)") == CAL_CRYPTO
    assert calendar_of("equity", "TSX") == CAL_TSX
    for market in ("NASDAQ", "NYSE", "NYSE Arca", "Cboe BZX"):
        assert calendar_of("equity", market) == CAL_US


def test_alignement_sans_remplissage():
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-02", "2024-01-03"]),
        "ticker": ["A", "A", "A", "B", "B"],
        "adj_close_cad": [1.0, 2.0, 3.0, 20.0, 30.0],
    })
    wide = align_prices(prices, ["A", "B"])
    assert list(wide.index) == list(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    assert not wide.isna().any().any()


def test_seances_sur_donnees_reelles(store):
    prices = with_calendar(store.prices("2026-11-12"))
    crypto, tsx, us = (sessions(prices, c) for c in (CAL_CRYPTO, CAL_TSX, CAL_US))
    assert len(crypto) == 1827
    assert set(tsx) != set(us)  # les jours fériés diffèrent
