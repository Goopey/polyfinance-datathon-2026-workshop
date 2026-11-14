"""Filtre published_at <= as_of ; délais de publication macro.
Conception : docs/04_DONNEES.md
"""
import pandas as pd
import pytest

from easytrade.data.point_in_time import filter_published, macro_published_at


def test_filtre_inclusif_sur_as_of():
    df = pd.DataFrame({"published_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]), "v": [1, 2, 3]})
    assert list(filter_published(df, "2024-01-02")["v"]) == [1, 2]


def test_delai_macro_mensuelle_applique():
    observed = pd.Series(pd.to_datetime(["2023-06-01"]))
    assert macro_published_at("CPIAUCSL", observed).iloc[0] == pd.Timestamp("2023-07-16")
    assert macro_published_at("UNRATE", observed).iloc[0] == pd.Timestamp("2023-07-08")
    assert macro_published_at("STATIC_TOTALCPICHANGE", observed).iloc[0] == pd.Timestamp("2023-07-26")


def test_serie_macro_inconnue_refusee():
    with pytest.raises(KeyError):
        macro_published_at("SERIE_INCONNUE", pd.Series(pd.to_datetime(["2023-06-01"])))


def test_macro_mensuelle_pas_disponible_avant_publication(store):
    as_of = "2023-06-30"
    cpi = store.macro(as_of, ["CPIAUCSL"])
    assert cpi["observed_at"].max() == pd.Timestamp("2023-05-01")  # juin non publié, mai publié le 16 juin
    assert (cpi["published_at"] <= pd.Timestamp(as_of)).all()
    latest = store.macro_latest(as_of, "CPIAUCSL")
    assert latest["observed_at"] == pd.Timestamp("2023-05-01")


def test_prix_et_change_coupes_a_as_of(store):
    as_of = pd.Timestamp("2023-06-30")
    assert store.prices(as_of)["date"].max() <= as_of
    assert store.fx(as_of)["date"].max() <= as_of
    assert store.corporate_actions(as_of)["ex_date"].max() <= as_of
    assert store.prices("2021-11-11").empty
