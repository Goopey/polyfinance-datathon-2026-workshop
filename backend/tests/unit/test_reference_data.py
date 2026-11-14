"""Cohérence des données de référence (personas, registre des sources, univers)."""
import csv

import pytest


def test_personas_sont_les_trois_du_case(personas):
    assert [p["id"] for p in personas["personas"]] == ["amira", "mateo", "robert"]


def test_poids_complets_et_normalises(personas):
    criteres = personas["_meta"]["criteres"]
    for p in personas["personas"]:
        assert sorted(p["poids"]) == sorted(criteres), p["id"]
        assert all(0 <= v <= 1 for v in p["poids"].values()), p["id"]
        assert sum(p["poids"].values()) == pytest.approx(1.0), p["id"]


def test_contraintes_bornees(personas):
    for p in personas["personas"]:
        c = p["contraintes"]
        for k in ("max_weight_per_asset", "max_weight_per_sector", "max_weight_crypto"):
            assert 0 <= c[k] <= 1, (p["id"], k)


def test_registre_des_sources_complet_pour_les_sources_utilisees(data_dir):
    with open(data_dir / "reference" / "sources_registry.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "registre vide"
    ids = [r["source_id"] for r in rows]
    assert len(ids) == len(set(ids)), "source_id en double"
    for r in rows:
        if r["statut"] == "utilisé":
            for champ in ("nom", "type_de_donnee", "date_extraction", "limites", "licence"):
                assert r[champ], (r["source_id"], champ)


def test_univers_du_jeu_de_depart(data_dir):
    chemin = data_dir / "raw" / "starter" / "assets_universe.csv"
    if not chemin.exists():
        pytest.skip("Jeu de départ absent de data/raw/starter/")
    with open(chemin, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 31
    assert {r["currency"] for r in rows} == {"CAD", "USD"}
