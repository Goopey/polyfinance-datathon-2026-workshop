"""Contrôles qualité et anomalie CNQ.TO."""
import pandas as pd

from easytrade.validation.data_quality import anomaly_notes, build_quality_report, split_anomalies


def _actions(rows):
    df = pd.DataFrame(rows, columns=["ex_date", "ticker", "action", "value", "unit"])
    df["ex_date"] = pd.to_datetime(df["ex_date"])
    return df


def test_detecte_les_fractionnements_invraisemblables():
    actions = _actions([
        ("2022-08-22", "CNQ.TO", "split", 1.021, "ratio"),
        ("2024-06-11", "CNQ.TO", "split", 2.0, "ratio"),
        ("2024-06-10", "NVDA", "split", 10.0, "ratio"),
        ("2023-01-01", "REV", "split", 0.5, "ratio"),
        ("2023-01-02", "RAR", "split", 0.98, "ratio"),
        ("2022-08-22", "CNQ.TO", "dividend", 0.75, "CAD"),
    ])
    found = split_anomalies(actions, 1.5)
    assert sorted(found["ticker"]) == ["CNQ.TO", "RAR"]
    assert list(anomaly_notes(actions, 1.5)) == ["CNQ.TO", "RAR"]
    assert "2022-08-22" in anomaly_notes(actions, 1.5)["CNQ.TO"]


def test_rapport_sur_donnees_reelles(store, settings):
    report = build_quality_report(store, settings.as_of, settings.quality)
    by_id = {c["id"]: c for c in report["checks"]}
    assert report["tickers"] == 31
    assert report["summary"]["fail"] == 0
    assert by_id["duplicates"]["status"] == "pass"
    assert by_id["fx_coverage"]["details"]["rows_without_rate"] == 0
    assert by_id["fx_coverage"]["details"]["rows_with_carried_rate"] > 0
    assert [d["ticker"] for d in by_id["split_anomalies"]["details"]] == ["CNQ.TO"]
    assert by_id["zero_volume"]["details"] == [{"date": "2022-07-06", "ticker": "ZST.TO"}]


def test_rapport_deterministe(store, settings):
    assert build_quality_report(store, settings.as_of, settings.quality) == build_quality_report(
        store, settings.as_of, settings.quality
    )
