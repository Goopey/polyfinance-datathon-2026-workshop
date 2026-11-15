"""Chargeur ESG : fichiers publics d'émissions de GES → lignes de data/reference/esg_evidence.csv.
Conception : docs/04_DONNEES.md, CONTRIBUTING.md (« Données ESG »)

Les cas de logique utilisent de petits fichiers synthétiques ; les contrôles sur les vraies données
sont ignorés si les fichiers bruts (non versionnés) sont absents de data/raw/external/.
"""
import csv
import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from easytrade.agents.tools import ResearchTools
from easytrade.data.external_esg import (
    CANADA_GLOB,
    EPA_PARENT_GLOB,
    EPA_ZIP_GLOB,
    EpaEmissions,
    EpaParents,
    ExternalFileError,
    find_file,
)
from easytrade.data.loaders import load_reference_table
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.ingestion.esg import (
    CANADA_PUBLISHED,
    ENTERED_BY,
    ESG_COLUMNS,
    build_epa_rows,
    build_esg_rows,
    check_sources,
    format_emissions,
    installations,
    merge_reference_file,
)

RETRIEVED = date(2026, 11, 15)
# Copie volontairement indépendante du code testé : si une constante du module change, ces tests le voient.
FIXTURE_SHEETS = {
    "Direct Point Emitters": "Total reported direct emissions",
    "Onshore Oil & Gas Prod.": "Total reported emissions from Onshore Oil & Gas Production",
    "Gathering & Boosting": "Total reported emissions from Gathering & Boosting",
    "Transmission Pipelines": "Total reported direct emissions from Transmission Pipelines",
    "LDC - Direct Emissions": "Total reported direct emissions from Local Distribution Companies",
    "SF6 from Elec. Equip.": "Total reported direct emissions from Electrical Equipment Use",
}
PARENT_HEADER = ("GHGRP FACILITY ID,FRS ID (FACILITY),REPORTING YEAR,FACILITY NAME,FACILITY ADDRESS,FACILITY CITY,"
                 "FACILITY STATE,FACILITY ZIP,FACILITY COUNTY,PARENT COMPANY NAME,PARENT CO. STREET ADDRESS,"
                 "PARENT CO. CITY,PARENT CO. STATE,PARENT CO. ZIP,PARENT CO. PERCENT OWNERSHIP,FACILITY NAICS CODE")


# --- fichiers synthétiques ---------------------------------------------------------------------
def _parent_line(facility_id, name, parent, pct, year=2023):
    return f"{facility_id},1,{year},{name},addr,city,TX,00000,county,{parent},street,city,TX,00000,{pct},211120"


def write_parents(directory: Path, lines, year=2023):
    text = PARENT_HEADER + "\n" + "\n".join(lines) + "\n"
    # cp1252, comme le fichier réel de l'EPA : « ’ » est l'octet 0x92, invalide en UTF-8.
    (directory / "ghgp_data_parent_company(2023).csv").write_bytes(text.encode("cp1252"))


def write_epa_zip(directory: Path, sheets: dict[str, list[tuple[int, str, float]]], year=2023,
                  stamp=(2024, 10, 15, 10, 39, 0)):
    """`sheets` : onglet -> [(id d'installation, nom, total)]. Un onglet « Suppliers » est toujours ajouté."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet, column in FIXTURE_SHEETS.items():
        ws = workbook.create_sheet(sheet)
        ws.append([f"Summary data collected by the Greenhouse Gas Reporting Program for {year}"])
        ws.append(["This data was reported to EPA by facilities as of 8/16/2024"])
        ws.append(["All emissions data is presented in units of metric tons of carbon dioxide equivalent"])
        ws.append(["Facility Id", "FRS Id", "Facility Name", "Reported State", column + " "])  # espace final, comme l'original
        for facility_id, name, total in sheets.get(sheet, []):
            ws.append([facility_id, 1, name, "TX", total])
    suppliers = workbook.create_sheet("Suppliers")
    suppliers.append([f"Summary data collected by the Greenhouse Gas Reporting Program for {year}"])
    suppliers.append(["x"])
    suppliers.append(["x"])
    suppliers.append(["Facility Id", "FRS Id", "Facility Name", "Reported State", "GHG Quantity"])
    suppliers.append([4, 1, "Fournisseur", "TX", 5_000_000])  # installation 4 = société mère XOM : ne doit jamais être comptée
    buffer = io.BytesIO()
    workbook.save(buffer)
    info = zipfile.ZipInfo(f"ghgp_data_{year}.xlsx", date_time=stamp)
    with zipfile.ZipFile(directory / "2023_data_summary_spreadsheets.zip", "w") as archive:
        archive.writestr(info, buffer.getvalue())


def write_canada(directory: Path, rows, name="GHGRP_UTF-8_EN_20261115151521.csv"):
    header = "Year,GHGRP ID,National Pollutant Release Inventory (NPRI) identifier,Company & facility name,NAICS,City,Province / territory,CO2,CH4,N2O,HFC,PFC,SF6,Total,CO2 bio"
    lines = [header]
    for year, facility_id, label, total in rows:
        lines.append(f'{year},{facility_id},0,"{label}",211,CALGARY,Alberta,{total},0,0,,,,{total},')
    (directory / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def external(tmp_path):
    parents = [
        _parent_line(1, "Baytown", "EXXON MOBIL CORP", 100),
        _parent_line(2, "Gas plant", "EXXON MOBIL CORP", 50),
        _parent_line(3, "Part inconnue", "EXXON MOBIL CORP", ""),
        _parent_line(4, "Fournisseur", "EXXON MOBIL CORP", 100),          # seulement dans « Suppliers » : pas d'émissions directes
        _parent_line(5, "Autre", "EXXON MOBIL CORPORATION", 100),          # nom proche mais différent : pas rattaché
        _parent_line(6, "Faux positif", "APPLETON PROPERTY VENTURES LLC", 100),
        _parent_line(7, "Gigafactory", "TESLA INC", 100),
        _parent_line(1, "Baytown", "EXXON MOBIL CORP", 100),               # doublon exact : compté une seule fois
    ]
    write_parents(tmp_path, parents)
    write_epa_zip(tmp_path, {
        "Direct Point Emitters": [(1, "Baytown", 1050.0), (3, "Part inconnue", 700.0), (7, "Gigafactory", 80.0), (5, "Autre", 50.0)],
        "Onshore Oil & Gas Prod.": [(2, "Gas plant", 400.0)],
        "SF6 from Elec. Equip.": [(2, "Gas plant", 100.0)],  # même installation, autre onglet : s'additionne
    })
    write_canada(tmp_path, [
        (2023, "G1", "Enbridge Gas Inc. - Distribution", 999_999),
        (2024, "G2", "Enbridge Gas Inc. - Distribution", 600_000),
        (2024, "G3", "Enbridge Pipelines Inc. - Station", 150_000),
        (2024, "G4", "FortisBC Energy Inc. - FortisBC Energy Inc.", 100_000),
        (2024, "G5", "Constellation Brands Schenley, ULC - Distillerie", 12_000),  # faux positif classique
        (2024, "G6", "Suncor Energy Products Partnership - Edmonton", 3_000_000),  # hors univers
    ])
    return tmp_path


def by_ticker(result):
    return {row["ticker"]: row for row in result.rows}


# --- logique -----------------------------------------------------------------------------------
def test_epa_ponderation_par_part_de_detention_et_somme_des_onglets(external):
    rows = by_ticker(build_esg_rows(external))
    xom = rows["XOM"]
    # 1050 (100 %) + (400 + 100) × 50 % = 1300 t ; l'installation sans part est exclue ; « Suppliers » jamais compté.
    assert xom["summary"].startswith("1,3 kt CO2e déclarées en 2023 par 2 installations américaines")
    assert "1 installation(s) sans part de détention déclarée, exclue(s)" in xom["excerpt"]
    assert "1 installation(s) liée(s) à la société mère sans émissions directes publiées" in xom["excerpt"]
    assert xom["claim_kind"] == "FAIT" and xom["source_id"] == "epa_ghgrp"
    assert rows["TSLA"]["summary"].startswith("0,1 kt CO2e déclarées en 2023 par 1 installation américaine ")


def test_epa_noms_de_societe_exacts_seulement(external):
    result = build_esg_rows(external)
    audit = result.audit["epa"]["tickers"]  # type: ignore[index]
    assert audit["XOM"]["parent_links"] == 4  # doublon retiré ; « EXXON MOBIL CORPORATION » et « APPLETON » non rattachés
    assert result.audit["epa"]["duplicate_parent_links"] == 1  # type: ignore[index]
    assert "AAPL" not in audit
    assert "PG" in audit and audit["PG"].get("row") is False  # aucune installation : pas de ligne, pas de zéro


def test_epa_date_de_publication_vient_de_l_archive(external):
    rows = by_ticker(build_esg_rows(external))
    assert rows["XOM"]["document_date"] == "2024-10-15"
    assert rows["XOM"]["retrieved_at"] == "2026-11-15"  # horodatage du nom du fichier canadien


def test_epa_classeur_de_l_annee_des_societes_meres_absent(tmp_path):
    write_parents(tmp_path, [_parent_line(1, "A", "EXXON MOBIL CORP", 100, year=2022)])
    write_epa_zip(tmp_path, {"Direct Point Emitters": [(1, "A", 10.0)]}, year=2023)
    write_canada(tmp_path, [(2024, "G1", "Enbridge Gas Inc. - X", 1)])
    with pytest.raises(ExternalFileError, match="ghgp_data_2022.xlsx"):
        build_esg_rows(tmp_path)


def test_epa_annees_differentes_refusees():
    table = pd.DataFrame({"facility_id": [1], "facility_name": ["A"], "state": ["TX"], "parent_name": ["X"],
                          "ownership_pct": [100.0], "emissions_tco2e": [1.0]})
    parents = EpaParents(table=table, year=2022, path=Path("p.csv"))
    emissions = EpaEmissions(table=table, year=2023, published_at=date(2024, 10, 15), path=Path("e.zip"), sheets_used=())
    with pytest.raises(ExternalFileError, match="Années différentes"):
        build_epa_rows(parents, emissions, RETRIEVED)


def test_canada_derniere_annee_et_rattachement_par_prefixe(external):
    result = build_esg_rows(external)
    rows = by_ticker(result)
    enb = rows["ENB.TO"]
    assert enb["summary"].startswith("750,0 kt CO2e déclarées en 2024 par 2 installations canadiennes")
    assert "Enbridge Gas Inc. (600,0 kt CO2e)" in enb["excerpt"] and "999" not in enb["summary"]  # 2023 ignoré
    assert enb["claim_kind"] == "HYPOTHESE" and enb["source_id"] == "canada_ghgrp"
    assert enb["document_date"] == CANADA_PUBLISHED[2024].isoformat()
    assert rows["FTS.TO"]["summary"].startswith("100,0 kt CO2e déclarées en 2024 par 1 installation canadienne ")
    assert "CNQ.TO" not in rows  # aucune installation : pas de ligne
    assert "Constellation" not in str(result.rows) and "Suncor" not in str(result.rows)


def test_canada_annee_sans_date_de_publication_refusee(tmp_path):
    write_parents(tmp_path, [_parent_line(1, "A", "EXXON MOBIL CORP", 100)])
    write_epa_zip(tmp_path, {"Direct Point Emitters": [(1, "A", 10.0)]})
    write_canada(tmp_path, [(2030, "G1", "Enbridge Gas Inc. - X", 1)])
    with pytest.raises(ExternalFileError, match="Date de publication inconnue"):
        build_esg_rows(tmp_path)


def test_fichier_manquant_message_clair(tmp_path):
    with pytest.raises(ExternalFileError, match="CONTRIBUTING.md"):
        find_file(tmp_path, EPA_PARENT_GLOB)
    for pattern in (EPA_ZIP_GLOB, CANADA_GLOB):
        with pytest.raises(ExternalFileError):
            find_file(tmp_path, pattern)


def test_univers_restreint_les_lignes(external):
    rows = by_ticker(build_esg_rows(external, universe={"XOM", "ENB.TO"}))
    assert set(rows) == {"XOM", "ENB.TO"}


def test_sortie_deterministe(external):
    assert build_esg_rows(external).rows == build_esg_rows(external).rows


def test_formats_francais():
    assert format_emissions(37_882_421.88) == "37,88 Mt CO2e"
    assert format_emissions(749_625.6) == "749,6 kt CO2e"
    assert installations(1, "américaine") == "1 installation américaine"
    assert installations(10, "canadienne") == "10 installations canadiennes"


# --- fichier de référence ----------------------------------------------------------------------
def test_fusion_conserve_les_lignes_manuelles_et_reecrit_celles_du_script(tmp_path, external):
    target = tmp_path / "esg_evidence.csv"
    manual = dict.fromkeys(ESG_COLUMNS, "")
    manual.update(ticker="ESGV", document_date="2026-08-31", signal_type="exclusions_indice", claim_kind="FAIT",
                  summary="Exclusions listées", source_id="etf_issuers", entered_by="Marie")
    stale = dict(manual, ticker="XOM", signal_type="ancienne_ligne", entered_by=ENTERED_BY)
    with open(target, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ESG_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows([manual, stale])

    rows = build_esg_rows(external).rows
    kept, written = merge_reference_file(target, rows)
    first = target.read_bytes()
    assert (kept, written) == (1, len(rows))
    with open(target, encoding="utf-8", newline="") as handle:
        content = list(csv.DictReader(handle))
    assert content[0]["entered_by"] == "Marie" and content[0]["ticker"] == "ESGV"
    assert all(r["signal_type"] != "ancienne_ligne" for r in content)
    assert merge_reference_file(target, rows) == (1, len(rows))
    assert target.read_bytes() == first  # idempotent


def test_fusion_refuse_un_fichier_aux_colonnes_inattendues(tmp_path):
    target = tmp_path / "esg_evidence.csv"
    target.write_text("ticker,autre\nXOM,1\n", encoding="utf-8")
    with pytest.raises(ExternalFileError, match="colonnes inattendues"):
        merge_reference_file(target, [])


def test_check_sources_signale_registre_incomplet(tmp_path):
    (tmp_path / "sources_registry.csv").write_text(
        "source_id,nom,url,type_de_donnee,date_extraction,couverture,frequence,traitements,limites,licence,"
        "conditions_url,redistribution_autorisee,statut,verifie_par,verifie_le\n"
        "epa_ghgrp,EPA,u,t,2026-11-15,,,,,,,,prévu,,\n", encoding="utf-8")
    registry = SourcesRegistry.load(tmp_path)
    problems = check_sources(registry, [{"source_id": "epa_ghgrp"}, {"source_id": "canada_ghgrp"}])
    assert problems == ["canada_ghgrp : absente du registre des sources",
                        "epa_ghgrp : statut « prévu » au lieu de « utilisé »"]


# --- données réelles du dépôt ------------------------------------------------------------------
def test_fichier_de_reference_est_coherent(settings, registry, store):
    """Chaque ligne d'esg_evidence.csv : titre de l'univers, source « utilisé », date valide, nature admise."""
    table = load_reference_table(settings.reference_dir, "esg_evidence.csv", "document_date")
    assert list(table.columns[:len(ESG_COLUMNS)]) == ESG_COLUMNS
    universe = set(store.assets()["ticker"])
    for _, row in table.iterrows():
        assert row["ticker"] in universe, row["ticker"]
        assert pd.notna(row["published_at"]), row["ticker"]
        assert row["claim_kind"] in {"FAIT", "HYPOTHESE", "SCENARIO"}, row["ticker"]
        assert row["source_id"] in registry and registry.get(row["source_id"]).statut == "utilisé", row["source_id"]
        assert row["document_url"].startswith("http"), row["ticker"]


def test_donnees_reelles_regenerent_le_fichier_de_reference(settings):
    external_dir = settings.data_dir / "raw" / "external"
    try:
        result = build_esg_rows(external_dir, universe=None)
    except ExternalFileError:
        pytest.skip("Fichiers ESG bruts absents de data/raw/external/ (non versionnés)")
    rows = by_ticker(result)
    assert {"XOM", "PG", "GOOGL", "TSLA", "ENB.TO", "CNQ.TO", "FTS.TO"} <= set(rows)
    assert rows["XOM"]["claim_kind"] == "FAIT" and rows["CNQ.TO"]["claim_kind"] == "HYPOTHESE"
    assert result.audit["canada"]["gas_sum_max_gap_tco2e"] < 1e-3  # type: ignore[index]
    committed = load_reference_table(settings.reference_dir, "esg_evidence.csv", "document_date")
    mine = committed[committed["entered_by"] == ENTERED_BY].sort_values(["ticker", "source_id"])
    assert list(mine["summary"]) == [r["summary"] for r in result.rows]


# --- consommation par l'outil de recherche (point-in-time) -------------------------------------
def _tools(settings, registry, store, as_of):
    ledger = EvidenceLedger(date.fromisoformat(as_of))
    return ResearchTools(store.assets(), as_of, settings.reference_dir, ledger, registry), ledger


def test_preuves_esg_filtrees_par_date_de_publication(settings, registry, store):
    tools, ledger = _tools(settings, registry, store, "2026-11-12")

    def from_source(found, book, source_id):
        return [r for r in found if book.get(r["evidence_id"]).source.source_id == source_id]

    xom = from_source(tools.preuves_esg("XOM"), ledger, "epa_ghgrp")
    assert len(xom) == 1 and xom[0]["document_date"] == "2024-10-15"
    evidence = ledger.get(xom[0]["evidence_id"])
    assert evidence.type == "esg" and evidence.claim_kind == "FAIT" and evidence.source.source_id == "epa_ghgrp"
    assert "Extraction par script" in evidence.processing
    assert "Installations américaines seulement" in evidence.limits  # les limites du registre accompagnent la preuve

    # Avant la publication du fichier EPA : aucune preuve (aucune fuite du futur, S5).
    early, early_ledger = _tools(settings, registry, store, "2024-10-14")
    assert early.preuves_esg("XOM") == [] and len(early_ledger) == 0

    # Le jeu canadien (HYPOTHESE) n'apparaît qu'à sa date de publication.
    before, before_ledger = _tools(settings, registry, store, "2026-05-26")
    after, after_ledger = _tools(settings, registry, store, "2026-05-27")
    assert from_source(before.preuves_esg("ENB.TO"), before_ledger, "canada_ghgrp") == []
    enb = from_source(after.preuves_esg("ENB.TO"), after_ledger, "canada_ghgrp")
    assert len(enb) == 1 and after_ledger.get(enb[0]["evidence_id"]).claim_kind == "HYPOTHESE"


def test_titre_sans_preuve_publiee_n_a_pas_de_preuve(settings, registry, store):
    """Aucune ligne publiée à la date d'analyse : aucune preuve (information manquante, jamais « zéro »).
    CSU.TO : page non datée, datée par prudence du jour de sa consultation (2026-11-15)."""
    tools, ledger = _tools(settings, registry, store, "2026-11-12")
    assert tools.preuves_esg("CSU.TO") == [] and len(ledger) == 0
