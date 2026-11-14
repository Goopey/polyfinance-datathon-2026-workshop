"""S5 — Aucune preuve avec published_at > as_of.
Conception : docs/09_SCENARIOS_TEST.md
"""
from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from easytrade.data.loaders import load_starter
from easytrade.data.point_in_time import PointInTimeStore
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.validation.metrics import compute_metrics_table

AS_OF_PASSE = date(2023, 6, 30)


@pytest.mark.scenario("S5")
def test_s05_aucune_fuite_du_futur(store, registry, settings):
    as_of = pd.Timestamp(AS_OF_PASSE)

    # Toutes les tables sont coupées à as_of.
    assert store.prices(as_of)["published_at"].max() <= as_of
    assert store.fx(as_of)["published_at"].max() <= as_of
    assert store.macro(as_of)["published_at"].max() <= as_of
    assert store.corporate_actions(as_of)["published_at"].max() <= as_of

    # Macro mensuelle : le mois de juin 2023 (observé le 2023-06-01) n'est pas encore publié le 30 juin.
    for series_id in ("CPIAUCSL", "UNRATE", "STATIC_TOTALCPICHANGE"):
        assert store.macro(as_of, [series_id])["observed_at"].max() < pd.Timestamp("2023-06-01")

    # Chaque preuve produite à cette date est publiée au plus à as_of.
    ledger = EvidenceLedger(AS_OF_PASSE)
    table = compute_metrics_table(store, as_of, ledger, registry, settings.quality)
    assert len(ledger) > 0
    assert all(e.published_at <= AS_OF_PASSE for e in ledger)
    assert all(e.window.end <= AS_OF_PASSE for e in ledger)
    assert pd.to_datetime(table["end"].dropna()).max() <= as_of

    # Le résultat ne dépend pas des données futures : même analyse sur un jeu amputé de tout ce qui suit as_of.
    data = load_starter(settings.starter_dir)
    tronque = replace(
        data,
        prices=data.prices[data.prices["date"] <= as_of],
        fx=data.fx[data.fx["date"] <= as_of],
        corporate_actions=data.corporate_actions[data.corporate_actions["ex_date"] <= as_of],
        macro=data.macro[data.macro["observed_at"] <= as_of],
    )
    ledger_tronque = EvidenceLedger(AS_OF_PASSE)
    table_tronque = compute_metrics_table(PointInTimeStore(tronque), as_of, ledger_tronque, registry, settings.quality)
    pd.testing.assert_frame_equal(table, table_tronque)
    assert ledger.to_records() == ledger_tronque.to_records()
