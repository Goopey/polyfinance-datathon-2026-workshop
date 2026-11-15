"""Preuves ESG datées et sourcées (data/reference/esg_evidence.csv).

Conception : docs/04_DONNEES.md (section 2, « ESG »), CONTRIBUTING.md (« Données ESG »)

Ce chargeur transforme deux fichiers publics d'émissions directes de gaz à effet de serre en lignes
de `esg_evidence.csv`, une par titre de l'univers et par source :
- États-Unis : EPA GHGRP, année 2023. Société mère et part de détention **déclarées** par chaque
  installation ; émission pondérée = émission de l'installation × part de détention ;
- Canada : ECCC GHGRP, dernière année du fichier. Rattachement **par le nom de l'exploitant**
  (hypothèse de l'équipe, `claim_kind = HYPOTHESE`) : pas de part de détention.

Règles :
- une seule date par ligne, la **date de publication** du document (filtre point-in-time) ;
- un titre sans installation déclarante n'a pas de ligne : c'est une information absente, pas « zéro » ;
- seules les lignes dont `entered_by` vaut `ENTERED_BY` sont réécrites ; les lignes saisies à la main
  sont conservées telles quelles ;
- sortie déterministe : deux exécutions sur les mêmes fichiers donnent le même fichier.

Ce chargeur ne note rien : il fournit des preuves sourcées. Leur transformation en signal du critère
`esg` (et le scénario S2) est une étape distincte du moteur.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from easytrade.data.external_esg import (
    CANADA_GLOB,
    EPA_PARENT_GLOB,
    EPA_ZIP_GLOB,
    CanadaFacilities,
    EpaEmissions,
    EpaParents,
    ExternalFileError,
    find_file,
    read_canada_facilities,
    read_epa_emissions,
    read_epa_parents,
)
from easytrade.data.sources_registry import SourcesRegistry

ENTERED_BY = "script:ingest_esg"
# Libellé lisible : il précède la phrase dans l'énoncé de la preuve montré à l'utilisateur (fiche d'un titre).
SIGNAL_TYPE = "Émissions directes de GES"
EPA_SOURCE = "epa_ghgrp"
CANADA_SOURCE = "canada_ghgrp"
ESG_COLUMNS = ["ticker", "document_date", "signal_type", "claim_kind", "summary", "excerpt", "document_title",
               "document_url", "source_id", "retrieved_at", "entered_by"]

EPA_TITLE = "GHGRP : 2023 Data Summary Spreadsheets et Reported Parent Companies (EPA)"
EPA_URL = "https://www.epa.gov/ghgreporting/data-sets"
CANADA_TITLE = "Greenhouse Gas (GHG) Emissions Data by Facility, 2004 à aujourd'hui (ECCC, PDGES)"
CANADA_URL = "https://open.canada.ca/data/en/dataset/a8ba14b7-7f23-462a-bdbb-83b0ef629823"

# Rattachement aux titres de l'univers. Hypothèses de l'équipe, à réviser avec un document cité.
# EPA : noms de sociétés mères **exacts** (majuscules) ; les recherches par mot ramènent des faux
# positifs (« APPLETON PROPERTY VENTURES », « RED APPLE GROUP »). Un titre absent n'a aucune
# installation déclarante sous ce nom.
EPA_PARENTS: dict[str, tuple[str, ...]] = {
    "XOM": ("EXXON MOBIL CORP",),
    "PG": ("THE PROCTER & GAMBLE CO",),
    "GOOGL": ("ALPHABET INC",),
    "TSLA": ("TESLA INC",),
}
# Canada : exploitant dont le nom **commence** par l'un de ces préfixes. Un exploitant filiale sous un
# autre nom n'est pas rattaché (ex. « Westcoast Energy Inc. » pour Enbridge) : le total est une borne
# inférieure.
CANADA_OPERATORS: dict[str, tuple[str, ...]] = {
    "ENB.TO": ("Enbridge",),
    "CNQ.TO": ("Canadian Natural",),
    "FTS.TO": ("Fortis",),
}
# Date de publication du jeu canadien par année de déclaration. Hypothèse prudente : date de dernière
# mise à jour de la fiche open.canada.ca relevée le 2026-11-15, à confirmer sur la fiche (« Date de
# publication »). Une date trop tardive ne fait jamais « fuiter » le futur ; une date trop précoce le ferait.
CANADA_PUBLISHED: dict[int, date] = {2024: date(2026, 5, 27)}


@dataclass
class EsgIngestion:
    rows: list[dict[str, str]]
    audit: dict[str, object] = field(default_factory=dict)


def _fr(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def installations(count: int, adjective: str) -> str:
    """« 1 installation américaine », « 10 installations américaines »."""
    return f"{count} installation{'s' if count > 1 else ''} {adjective}{'s' if count > 1 else ''}"


def format_share(percent: float) -> str:
    """Part de détention : « 100 % », « 28,1 % »."""
    return f"{percent:g}".replace(".", ",") + " %"


def format_emissions(tonnes: float) -> str:
    """« 4,87 Mt CO2e » à partir d'un million de tonnes ; sinon en kt (« 157,3 kt CO2e »)."""
    if tonnes >= 1_000_000:
        return f"{_fr(tonnes / 1_000_000, 2)} Mt CO2e"
    return f"{_fr(tonnes / 1_000, 1)} kt CO2e"


def _row(*, ticker: str, published: date, claim_kind: str, summary: str, excerpt: str, title: str, url: str,
         source_id: str, retrieved_at: date) -> dict[str, str]:
    return {
        "ticker": ticker, "document_date": published.isoformat(), "signal_type": SIGNAL_TYPE,
        "claim_kind": claim_kind, "summary": summary, "excerpt": excerpt, "document_title": title,
        "document_url": url, "source_id": source_id, "retrieved_at": retrieved_at.isoformat(),
        "entered_by": ENTERED_BY,
    }


# --- États-Unis --------------------------------------------------------------------------------
def build_epa_rows(parents: EpaParents, emissions: EpaEmissions, retrieved_at: date,
                   universe: Optional[set[str]] = None) -> tuple[list[dict[str, str]], dict[str, object]]:
    if parents.year != emissions.year:
        raise ExternalFileError(
            f"Années différentes : sociétés mères {parents.year}, émissions {emissions.year}. Les deux fichiers doivent porter sur la même année."
        )
    year = emissions.year
    links = parents.table.drop_duplicates(["facility_id", "parent_name"])
    rows: list[dict[str, str]] = []
    audit: dict[str, object] = {"year": year, "published_at": emissions.published_at.isoformat(),
                                "duplicate_parent_links": int(len(parents.table) - len(links)), "tickers": {}}
    for ticker in sorted(EPA_PARENTS):
        if universe is not None and ticker not in universe:
            continue
        mine = links[links["parent_name"].isin(EPA_PARENTS[ticker])]
        joined = mine.merge(emissions.table[["facility_id", "emissions_tco2e"]], on="facility_id", how="inner")
        known = joined[joined["ownership_pct"].notna()].copy()
        unknown_share = int(joined["ownership_pct"].isna().sum())
        entry = {"parent_links": int(len(mine)), "with_direct_emissions": int(len(joined)),
                 "unknown_ownership": unknown_share}
        audit["tickers"][ticker] = entry  # type: ignore[index]
        if known.empty:
            entry["row"] = False
            continue
        known["weighted"] = known["emissions_tco2e"] * known["ownership_pct"] / 100.0
        total = float(known["weighted"].sum())
        top = known.sort_values(["weighted", "facility_id"], ascending=[False, True]).iloc[0]
        entry.update({"row": True, "facilities": int(len(known)), "weighted_tco2e": round(total, 3)})
        names = ", ".join(sorted(EPA_PARENTS[ticker]))
        excerpt = (
            f"Société mère déclarée : {names}. Plus importante installation : {top['facility_name']} "
            f"({format_emissions(float(top['weighted']))}, part de détention {format_share(float(top['ownership_pct']))})."
        )
        outside = len(mine) - len(joined)
        if outside:
            excerpt += (f" {outside} installation(s) liée(s) à la société mère sans émissions directes publiées "
                        "(fournisseurs, injection de CO2), non comptée(s).")
        if unknown_share:
            excerpt += f" {unknown_share} installation(s) sans part de détention déclarée, exclue(s) du total."
        rows.append(_row(
            ticker=ticker, published=emissions.published_at, claim_kind="FAIT",
            summary=(f"{format_emissions(total)} déclarées en {year} par {installations(len(known), 'américaine')} "
                     f"(pondérées par la part de détention de la société mère)."),
            excerpt=excerpt, title=EPA_TITLE, url=EPA_URL, source_id=EPA_SOURCE, retrieved_at=retrieved_at,
        ))
    return rows, audit


# --- Canada ------------------------------------------------------------------------------------
def build_canada_rows(canada: CanadaFacilities, retrieved_at: date,
                      universe: Optional[set[str]] = None) -> tuple[list[dict[str, str]], dict[str, object]]:
    table = canada.table
    year = int(table["year"].max())
    if year not in CANADA_PUBLISHED:
        raise ExternalFileError(
            f"Date de publication inconnue pour l'année {year} : l'ajouter à CANADA_PUBLISHED (ingestion/esg.py) après avoir lu la fiche open.canada.ca."
        )
    published = CANADA_PUBLISHED[year]
    latest = table[table["year"] == year].copy()
    latest["operator_key"] = latest["operator"].str.lower()
    rows: list[dict[str, str]] = []
    audit: dict[str, object] = {"year": year, "published_at": published.isoformat(), "facilities_in_year": int(len(latest)),
                                "total_tco2e": round(float(latest["total_tco2e"].sum()), 3),
                                "gas_sum_max_gap_tco2e": canada.gas_sum_max_gap, "tickers": {}}
    for ticker in sorted(CANADA_OPERATORS):
        if universe is not None and ticker not in universe:
            continue
        mask = pd.Series(False, index=latest.index)
        for prefix in CANADA_OPERATORS[ticker]:
            mask |= latest["operator_key"].str.startswith(prefix.lower())
        mine = latest[mask]
        operators = sorted(mine["operator"].unique())
        entry: dict[str, object] = {"operators": operators, "facilities": int(len(mine))}
        audit["tickers"][ticker] = entry  # type: ignore[index]
        valid = mine.dropna(subset=["total_tco2e"])
        if valid.empty:
            entry["row"] = False
            continue
        total = float(valid["total_tco2e"].sum())
        entry.update({"row": True, "total_tco2e": round(total, 3)})
        by_operator = valid.groupby("operator")["total_tco2e"].sum().sort_values(ascending=False)
        detail = " ; ".join(f"{name} ({format_emissions(float(value))})" for name, value in by_operator.head(3).items())
        rows.append(_row(
            ticker=ticker, published=published, claim_kind="HYPOTHESE",
            summary=(f"{format_emissions(total)} déclarées en {year} par {installations(len(valid), 'canadienne')} "
                     f"dont l'exploitant porte le nom de la société (rattachement par le nom, sans part de détention)."),
            excerpt=f"Exploitants retenus : {detail}.", title=CANADA_TITLE, url=CANADA_URL, source_id=CANADA_SOURCE,
            retrieved_at=retrieved_at,
        ))
    return rows, audit


# --- Assemblage et écriture --------------------------------------------------------------------
def build_esg_rows(external_dir: Path, retrieved_at: Optional[date] = None,
                   universe: Optional[set[str]] = None) -> EsgIngestion:
    """Lit les fichiers de `external_dir` et construit les lignes (sans rien écrire)."""
    parents = read_epa_parents(find_file(external_dir, EPA_PARENT_GLOB))
    emissions = read_epa_emissions(find_file(external_dir, EPA_ZIP_GLOB), parents.year)
    canada = read_canada_facilities(find_file(external_dir, CANADA_GLOB))
    retrieved = retrieved_at or canada.retrieved_on
    if retrieved is None:
        raise ExternalFileError("Date d'extraction inconnue : la fournir (--retrieved-at AAAA-MM-JJ).")
    epa_rows, epa_audit = build_epa_rows(parents, emissions, retrieved, universe)
    ca_rows, ca_audit = build_canada_rows(canada, retrieved, universe)
    rows = sorted(epa_rows + ca_rows, key=lambda r: (r["ticker"], r["source_id"]))
    return EsgIngestion(rows=rows, audit={
        "retrieved_at": retrieved.isoformat(),
        "epa": epa_audit, "canada": ca_audit,
        "epa_sheets": list(emissions.sheets_used),
    })


def check_sources(registry: SourcesRegistry, rows: list[dict[str, str]]) -> list[str]:
    """Sources des lignes qui ne sont pas au registre avec le statut « utilisé » (règle 3 de CONTRIBUTING.md)."""
    problems = []
    for source_id in sorted({r["source_id"] for r in rows}):
        if source_id not in registry:
            problems.append(f"{source_id} : absente du registre des sources")
        elif registry.get(source_id).statut != "utilisé":
            problems.append(f"{source_id} : statut « {registry.get(source_id).statut} » au lieu de « utilisé »")
    return problems


def merge_reference_file(path: Path, new_rows: list[dict[str, str]]) -> tuple[int, int]:
    """Réécrit `esg_evidence.csv` : lignes manuelles conservées, lignes du script remplacées.

    Retourne (lignes manuelles conservées, lignes du script écrites).
    """
    kept: list[dict[str, str]] = []
    if path.exists():
        with open(path, encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and list(reader.fieldnames) != ESG_COLUMNS:
                raise ExternalFileError(f"{path.name} : colonnes inattendues {reader.fieldnames}")
            kept = [row for row in reader if row.get("entered_by") != ENTERED_BY]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ESG_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
        writer.writerows(new_rows)
    return len(kept), len(new_rows)
