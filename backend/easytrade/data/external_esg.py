"""Lecture des fichiers publics d'émissions de GES déposés dans `data/raw/external/`.

Conception : docs/04_DONNEES.md (section 2, ligne « ESG »), CONTRIBUTING.md (« Données ESG »)
Deux sources, aucune cote commerciale :
- EPA GHGRP (États-Unis) : classeur « 2023 Data Summary Spreadsheets » (zip) + fichier « Reported
  Parent Companies » (société mère et part de détention de chaque installation) ;
- ECCC GHGRP (Canada) : « Greenhouse Gas (GHG) Emissions Data by Facility », CSV par installation.

Ce module ne fait que lire et normaliser (règle 1 : seul `easytrade/data/` lit les fichiers de
données). Le rattachement des installations aux titres de l'univers est dans `ingestion/esg.py`.
Les fichiers bruts ne sont jamais versionnés (`.gitignore`).
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

EPA_PARENT_GLOB = "ghgp_data_parent_company*.csv"
EPA_ZIP_GLOB = "*data_summary_spreadsheets*.zip"
CANADA_GLOB = "GHGRP_UTF-8_EN_*.csv"

# Onglets d'émissions **directes** du classeur de l'EPA → colonne du total. La FAQ de l'EPA (question 12)
# explique que ces catégories sont publiées dans des onglets distincts du même programme : on les
# additionne par installation. « Suppliers » (quantités liées aux produits vendus), « CO2 Injection »
# et « Geologic Sequestration » ne sont pas des émissions directes et sont exclus.
EPA_DIRECT_SHEETS: dict[str, str] = {
    "Direct Point Emitters": "Total reported direct emissions",
    "Onshore Oil & Gas Prod.": "Total reported emissions from Onshore Oil & Gas Production",
    "Gathering & Boosting": "Total reported emissions from Gathering & Boosting",
    "Transmission Pipelines": "Total reported direct emissions from Transmission Pipelines",
    "LDC - Direct Emissions": "Total reported direct emissions from Local Distribution Companies",
    "SF6 from Elec. Equip.": "Total reported direct emissions from Electrical Equipment Use",
}
EPA_WORKBOOK = "ghgp_data_{year}.xlsx"
CANADA_GASES = ["CO2", "CH4", "N2O", "HFC", "PFC", "SF6"]
CANADA_FILENAME_STAMP = re.compile(r"(\d{4})(\d{2})(\d{2})\d{6}")


class ExternalFileError(ValueError):
    """Fichier absent, format inattendu ou incohérence entre fichiers."""


def find_file(external_dir: Path, pattern: str) -> Path:
    """Fichier correspondant au motif ; en cas de plusieurs, le dernier par ordre alphabétique."""
    matches = sorted(Path(external_dir).glob(pattern))
    if not matches:
        raise ExternalFileError(
            f"Aucun fichier « {pattern} » dans {external_dir}. Voir CONTRIBUTING.md, section « Données ESG »."
        )
    return matches[-1]


def _read_text_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Lit un CSV en essayant UTF-8, puis cp1252 (fichiers Windows de l'EPA), puis latin-1."""
    last: Optional[Exception] = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as error:
            last = error
    raise ExternalFileError(f"Encodage illisible : {path}") from last


# --- EPA ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EpaParents:
    table: pd.DataFrame  # facility_id, facility_name, state, parent_name, ownership_pct
    year: int
    path: Path


@dataclass(frozen=True)
class EpaEmissions:
    table: pd.DataFrame  # facility_id, facility_name, state, emissions_tco2e (somme des onglets directs)
    year: int
    published_at: date   # date du fichier dans l'archive (publication par l'EPA)
    path: Path
    sheets_used: tuple[str, ...]


def read_epa_parents(path: Path) -> EpaParents:
    raw = _read_text_csv(path)
    needed = {"GHGRP FACILITY ID", "FACILITY NAME", "FACILITY STATE", "PARENT COMPANY NAME",
              "PARENT CO. PERCENT OWNERSHIP", "REPORTING YEAR"}
    missing = needed - set(raw.columns)
    if missing:
        raise ExternalFileError(f"{path.name} : colonnes absentes {sorted(missing)}")
    years = sorted(raw["REPORTING YEAR"].dropna().astype(int).unique())
    if len(years) != 1:
        raise ExternalFileError(f"{path.name} : une seule année de déclaration attendue, trouvé {years}")
    table = pd.DataFrame({
        "facility_id": raw["GHGRP FACILITY ID"].astype("int64"),
        "facility_name": raw["FACILITY NAME"].astype(str).str.strip(),
        "state": raw["FACILITY STATE"].astype(str).str.strip(),
        "parent_name": raw["PARENT COMPANY NAME"].astype(str).str.strip().str.upper(),
        "ownership_pct": pd.to_numeric(raw["PARENT CO. PERCENT OWNERSHIP"], errors="coerce"),
    })
    return EpaParents(table=table, year=int(years[0]), path=path)


def _sheet_with_header(workbook: bytes, sheet: str) -> tuple[pd.DataFrame, Optional[int]]:
    """Feuille lue à partir de la ligne d'en-tête (celle dont la première cellule est « Facility Id »)."""
    head = pd.read_excel(io.BytesIO(workbook), sheet_name=sheet, header=None, nrows=8)
    header_row = next((i for i in range(len(head)) if str(head.iat[i, 0]).strip() == "Facility Id"), None)
    if header_row is None:
        raise ExternalFileError(f"Onglet « {sheet} » : ligne d'en-tête « Facility Id » introuvable")
    year = None
    match = re.search(r"for (\d{4})", str(head.iat[0, 0]))
    if match:
        year = int(match.group(1))
    table = pd.read_excel(io.BytesIO(workbook), sheet_name=sheet, header=header_row)
    table.columns = [str(c).strip() for c in table.columns]
    return table, year


def read_epa_emissions(zip_path: Path, year: int) -> EpaEmissions:
    """Émissions directes par installation : somme des onglets directs du classeur de l'année `year`.

    La date de publication est la date du fichier dans l'archive (non modifiable par l'équipe),
    ce qui évite d'inventer une date.
    """
    member = EPA_WORKBOOK.format(year=year)
    with zipfile.ZipFile(zip_path) as archive:
        try:
            info = archive.getinfo(member)
        except KeyError as error:
            raise ExternalFileError(f"{zip_path.name} ne contient pas {member}") from error
        workbook = archive.read(member)
    published = date(*info.date_time[:3])

    parts: list[pd.DataFrame] = []
    for sheet, column in EPA_DIRECT_SHEETS.items():
        table, sheet_year = _sheet_with_header(workbook, sheet)
        if sheet_year is not None and sheet_year != year:
            raise ExternalFileError(f"Onglet « {sheet} » : année {sheet_year}, attendue {year}")
        if column not in table.columns:
            raise ExternalFileError(f"Onglet « {sheet} » : colonne « {column} » absente (colonnes : {list(table.columns)[:15]})")
        name_column = "Facility Name"
        state_column = "State" if "State" in table.columns else "Reported State"
        part = pd.DataFrame({
            "facility_id": pd.to_numeric(table["Facility Id"], errors="coerce"),
            "facility_name": table[name_column].astype(str).str.strip(),
            "state": table[state_column].astype(str).str.strip(),
            "emissions_tco2e": pd.to_numeric(table[column], errors="coerce"),
        }).dropna(subset=["facility_id"])
        part["facility_id"] = part["facility_id"].astype("int64")
        part["emissions_tco2e"] = part["emissions_tco2e"].fillna(0.0)
        parts.append(part)

    stacked = pd.concat(parts, ignore_index=True)
    names = stacked.drop_duplicates("facility_id").set_index("facility_id")[["facility_name", "state"]]
    totals = stacked.groupby("facility_id", sort=True)["emissions_tco2e"].sum()
    table = names.join(totals).reset_index().sort_values("facility_id", kind="mergesort").reset_index(drop=True)
    return EpaEmissions(table=table, year=year, published_at=published, path=zip_path,
                        sheets_used=tuple(EPA_DIRECT_SHEETS))


# --- Canada ------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CanadaFacilities:
    table: pd.DataFrame  # year, facility_id, operator, facility_label, province, total_tco2e
    retrieved_on: Optional[date]  # horodatage inscrit dans le nom du fichier téléchargé
    path: Path
    gas_sum_max_gap: float  # écart maximal entre « Total » et la somme des gaz (contrôle)


def read_canada_facilities(path: Path) -> CanadaFacilities:
    raw = _read_text_csv(path, dtype={"GHGRP ID": "string"})
    needed = {"Year", "GHGRP ID", "Company & facility name", "Province / territory", "Total", *CANADA_GASES}
    missing = needed - set(raw.columns)
    if missing:
        raise ExternalFileError(f"{path.name} : colonnes absentes {sorted(missing)}")
    label = raw["Company & facility name"].astype(str).str.strip()
    table = pd.DataFrame({
        "year": raw["Year"].astype("int64"),
        "facility_id": raw["GHGRP ID"].astype(str).str.strip(),
        # « Exploitant - installation » : l'exploitant est ce qui précède le premier « - ».
        "operator": label.str.split(" - ", n=1).str[0].str.strip(),
        "facility_label": label,
        "province": raw["Province / territory"].astype(str).str.strip(),
        "total_tco2e": pd.to_numeric(raw["Total"], errors="coerce"),
    })
    gap = float((pd.to_numeric(raw["Total"], errors="coerce")
                 - raw[CANADA_GASES].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)).abs().max())
    stamp = CANADA_FILENAME_STAMP.search(path.name)
    retrieved = date(int(stamp.group(1)), int(stamp.group(2)), int(stamp.group(3))) if stamp else None
    return CanadaFacilities(table=table, retrieved_on=retrieved, path=path, gas_sum_max_gap=gap)
