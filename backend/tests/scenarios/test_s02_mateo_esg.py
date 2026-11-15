"""S2 — Mateo : l'ESG change le résultat.

Conception : docs/09_SCENARIOS_TEST.md, docs/03_DECISION_ENGINE.md (section « Critère ESG »)
Données réelles : preuves d'émissions de GES (EPA, ECCC) de data/reference/esg_evidence.csv et
classification de l'univers. La controverse du point 1 est une ligne **de test** ajoutée dans une
copie temporaire du dossier de référence : le dépôt n'en contient aucune.
"""
import copy
import csv
import shutil

import pytest

from easytrade.agents.simulated import simulated_client
from easytrade.config import Settings
from easytrade.orchestration.pipeline import Workspace, run_pipeline

TECH = {"SHOP.TO", "CSU.TO", "AAPL", "MSFT", "NVDA", "GOOGL"}


def _items(run):
    return {item.ticker: item for item in run.explanation.items}


@pytest.mark.scenario("S2")
def test_s02_1_controverse_documentee_ecartee_preuve_citee(workspace, tmp_path):
    reference = tmp_path / "reference"
    shutil.copytree(workspace.settings.reference_dir, reference)
    with open(reference / "esg_evidence.csv", "a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([
            "JNJ", "2025-03-01", "Controverse sociale", "FAIT", "Ligne de test (controverse fictive).",
            "Extrait de test.", "Document fictif de test", "https://example.org/test", "epa_ghgrp",
            "2026-11-15", "test",
        ])
    ws = Workspace(settings=Settings(data_dir=tmp_path), store=workspace.store, registry=workspace.registry,
                   personas=workspace.personas, forbidden=workspace.forbidden)
    run = run_pipeline("mateo", client=simulated_client(), workspace=ws)
    assert run.status == "termine", run.error
    rejected = {r.ticker: r for r in run.explanation.rejected}
    assert "JNJ" in rejected and "controverse" in rejected["JNJ"].reason
    cited = [run.ledger.get(i) for i in rejected["JNJ"].evidence_ids]
    assert any(e.type == "esg" and "Controverse sociale" in e.statement for e in cited)
    assert "JNJ" not in _items(run)
    # Sans la ligne, JNJ fait partie des pistes : c'est bien la controverse qui l'écarte.
    assert "JNJ" not in {r.ticker for r in run_pipeline("mateo", client=simulated_client(),
                                                          workspace=workspace).decision.rejected}


@pytest.mark.scenario("S2")
def test_s02_1_emetteurs_majeurs_ecartes_preuves_datees(pipeline_run):
    run = pipeline_run("mateo")
    rejected = {r.ticker: r for r in run.explanation.rejected}
    for ticker in ("XOM", "CNQ.TO"):
        cited = [run.ledger.get(i) for i in rejected[ticker].evidence_ids]
        emissions = [e for e in cited if e.type == "esg" and e.statement.startswith("Émissions directes de GES")]
        assert emissions and all(e.published_at <= run.as_of for e in emissions)
        assert any(e.claim_kind == "HYPOTHESE" and e.unit == "Mt CO2e" for e in cited)  # seuil de l'équipe
        assert any(e.type == "profile" for e in cited)  # phrase du profil qui fonde la règle


@pytest.mark.scenario("S2")
def test_s02_2_aucune_piste_crypto(pipeline_run):
    run = pipeline_run("mateo")
    assert not {"BTC-USD", "ETH-USD"} & set(_items(run))
    assert {"BTC-USD", "ETH-USD"} <= {r.ticker for r in run.explanation.rejected}


@pytest.mark.scenario("S2")
def test_s02_3_poids_esg_a_zero_change_le_classement(workspace, pipeline_run):
    with_esg = pipeline_run("mateo")
    personas = copy.deepcopy(workspace.personas)
    mateo = next(p for p in personas["personas"] if p["id"] == "mateo")
    esg = mateo["poids"].pop("esg")
    mateo["poids"] = {k: v / (1 - esg) for k, v in mateo["poids"].items()} | {"esg": 0.0}
    ws = Workspace(settings=workspace.settings, store=workspace.store, registry=workspace.registry,
                   personas=personas, forbidden=workspace.forbidden)
    without = run_pipeline("mateo", client=simulated_client(), workspace=ws)
    assert without.status == "termine", without.error
    order = [c.ticker for c in with_esg.decision.ranking]
    order_without = [c.ticker for c in without.decision.ranking]
    assert order != order_without
    # La différence est affichable : elle tient à la contribution du critère ESG, visible par piste.
    assert order[0] == "ESGV" and order_without[0] != "ESGV"
    assert _items(with_esg)["ESGV"].contributions["esg"] > 0


@pytest.mark.scenario("S2")
def test_s02_4_sans_donnee_esg_information_manquante(pipeline_run):
    run = pipeline_run("mateo")
    items = _items(run)
    by_ticker = {c.ticker: c for c in run.decision.ranking}
    without_esg = [t for t in items if "esg" in by_ticker[t].missing_criteria]
    assert without_esg  # la couverture ESG est partielle : c'est affiché, pas masqué
    for ticker in without_esg:
        assert any("preuve ESG" in u for u in items[ticker].unknowns)
        assert items[ticker].confidence != "élevée"
        assert items[ticker].contributions.get("esg", 0.0) == 0.0  # jamais un bon score
    # Émissions sous le seuil (borne inférieure) : preuve visible, critère manquant (pas « conforme »).
    assert "esg" in by_ticker["FTS.TO"].missing_criteria


@pytest.mark.scenario("S2")
def test_s02_5_technologies_presentes_ou_ecartees_avec_motif(pipeline_run):
    run = pipeline_run("mateo")
    items, rejected = _items(run), {r.ticker: r for r in run.explanation.rejected}
    for ticker in TECH:
        assert ticker in items or (ticker in rejected and rejected[ticker].evidence_ids), ticker


@pytest.mark.scenario("S2")
def test_s02_point_in_time_emissions_pas_encore_publiees(pipeline_run):
    """2024-06-28 : ni le fichier de l'EPA (2024-10-15) ni celui d'ECCC (2026-05-27) ne sont publiés."""
    run = pipeline_run("mateo", None, "2024-06-28")
    assert run.status == "termine", run.error
    assert not [r for r in run.decision.rejected if r.rule == "esg_emissions"]
    assert all(e.published_at <= run.as_of for e in run.ledger)
