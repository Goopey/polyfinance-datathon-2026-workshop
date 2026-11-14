"""S7 — Devises, adj_close, fractionnements, calendriers.
Conception : docs/09_SCENARIOS_TEST.md
"""
import numpy as np
import pandas as pd
import pytest

from easytrade.data.calendar import annualization_factor
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.validation.metrics import compute_metrics_table


@pytest.fixture(scope="module")
def prices(store, settings):
    return store.prices(settings.as_of)


@pytest.mark.scenario("S7")
def test_s07_1_agregations_en_cad_et_dernier_taux_connu(prices, store, settings):
    aapl = prices[prices["ticker"] == "AAPL"].set_index("date")
    fx = store.fx(settings.as_of).set_index("date")["usdcad"]

    # Jour avec taux : taux du jour.
    jour = pd.Timestamp("2024-03-15")
    assert aapl.loc[jour, "adj_close_cad"] == pytest.approx(aapl.loc[jour, "adj_close"] * fx.loc[jour])
    assert not aapl.loc[jour, "fx_carried"]

    # Jours fériés canadiens ouverts aux États-Unis : dernier taux connu, signalé, jamais un taux futur.
    sans_taux = aapl.index.difference(fx.index)
    assert len(sans_taux) > 0
    for day in sans_taux:
        precedent = fx[fx.index < day].index.max()
        assert aapl.loc[day, "fx_rate"] == fx.loc[precedent]
        assert aapl.loc[day, "fx_date"] == precedent < day
        assert aapl.loc[day, "fx_carried"]

    # Un actif coté en CAD n'est pas converti.
    ry = prices[prices["ticker"] == "RY.TO"]
    assert (ry["fx_rate"] == 1.0).all() and (ry["adj_close_cad"] == ry["adj_close"]).all()

    # Les indicateurs sont en CAD, y compris pour un actif en USD.
    ledger = EvidenceLedger(settings.as_of)
    table = compute_metrics_table(store, settings.as_of, ledger, registry=_registry(settings), tickers=["AAPL"])
    assert set(table["currency"]) == {"CAD"}
    assert all(e.currency == "CAD" for e in ledger)


def _registry(settings):
    from easytrade.data.sources_registry import SourcesRegistry

    return SourcesRegistry.load(settings.reference_dir)


@pytest.mark.scenario("S7")
def test_s07_2_rendements_sur_adj_close(prices, store, settings):
    # À une date ex-dividende, adj_close et close ne donnent pas le même rendement : on utilise adj_close.
    actions = store.corporate_actions(settings.as_of)
    div = actions[(actions["ticker"] == "AAPL") & (actions["action"] == "dividend")].iloc[0]
    aapl = prices[prices["ticker"] == "AAPL"].set_index("date").sort_index()
    r_adj = aapl["adj_close"].pct_change().loc[div["ex_date"]]
    r_close = aapl["close"].pct_change().loc[div["ex_date"]]
    assert r_adj != pytest.approx(r_close, abs=1e-12)

    ledger = EvidenceLedger(settings.as_of)
    compute_metrics_table(store, settings.as_of, ledger, _registry(settings), tickers=["AAPL"])
    assert all("adj_close" in e.processing for e in ledger)
    # Le rendement annualisé de la preuve vient de adj_close, pas de close.
    evidence = next(e for e in ledger if e.produced_by.endswith("annualized_return@v1") and "toute la période" in e.statement)
    n = len(aapl) - 1
    attendu = ((aapl["adj_close"] * aapl["fx_rate"]).iloc[-1] / (aapl["adj_close"] * aapl["fx_rate"]).iloc[0]) ** (252 / n) - 1
    assert evidence.value == pytest.approx(attendu * 100, rel=1e-9)
    avec_close = ((aapl["close"] * aapl["fx_rate"]).iloc[-1] / (aapl["close"] * aapl["fx_rate"]).iloc[0]) ** (252 / n) - 1
    assert evidence.value != pytest.approx(avec_close * 100, rel=1e-6)


@pytest.mark.scenario("S7")
def test_s07_3_fractionnements_non_reappliques(prices, store, settings):
    actions = store.corporate_actions(settings.as_of)
    splits = actions[actions["action"] == "split"]
    assert len(splits) == 7
    for split in splits.itertuples():
        serie = prices[prices["ticker"] == split.ticker].set_index("date").sort_index()
        for colonne in ("close", "adj_close"):
            rendement = serie[colonne].pct_change().loc[split.ex_date]
            # Un fractionnement réappliqué produirait un saut de -50 % à -95 % ce jour-là.
            assert abs(rendement) < 0.25, (split.ticker, split.ex_date, colonne, rendement)


@pytest.mark.scenario("S7")
def test_s07_4_annualisation_selon_le_calendrier(store, settings, registry):
    assert annualization_factor("crypto") == 365
    assert annualization_factor("equity") == 252

    ledger = EvidenceLedger(settings.as_of)
    table = compute_metrics_table(store, settings.as_of, ledger, registry, tickers=["BTC-USD", "SPY"])
    prices = store.prices(settings.as_of, ["BTC-USD", "SPY"])
    for ticker, facteur in (("BTC-USD", 365), ("SPY", 252)):
        serie = prices[prices["ticker"] == ticker].set_index("date")["adj_close_cad"].sort_index()
        attendu = serie.pct_change().dropna().std(ddof=1) * np.sqrt(facteur) * 100
        ligne = table[(table["ticker"] == ticker) & (table["metric"] == "annualized_volatility") & (table["window"] == "full")]
        assert ligne["value"].iloc[0] == pytest.approx(attendu, rel=1e-9)
        evidence = ledger.get(ligne["evidence_id"].iloc[0])
        assert f"{facteur} périodes par an" in evidence.processing
