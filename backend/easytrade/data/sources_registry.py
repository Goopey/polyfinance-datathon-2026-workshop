"""Lecture du registre des sources (data/reference/sources_registry.csv).

Conception : docs/04_DONNEES.md section 3
Une source doit figurer au registre avant d'alimenter une preuve.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from easytrade.schemas.evidence import EvidenceSource

STATUT_UTILISE = "utilisé"


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    nom: str
    url: str
    type_de_donnee: str
    date_extraction: Optional[date]
    traitements: str
    limites: str
    licence: str
    statut: str

    def as_evidence_source(self) -> EvidenceSource:
        url = self.url if self.url and self.url != "n/a" else None
        return EvidenceSource(source_id=self.source_id, name=self.nom, url=url)


class SourcesRegistry:
    def __init__(self, records: dict[str, SourceRecord]):
        self._records = records

    @classmethod
    def load(cls, reference_dir: Path) -> "SourcesRegistry":
        records: dict[str, SourceRecord] = {}
        with open(reference_dir / "sources_registry.csv", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                extraction = row["date_extraction"].strip()
                records[row["source_id"]] = SourceRecord(
                    source_id=row["source_id"],
                    nom=row["nom"],
                    url=row["url"],
                    type_de_donnee=row["type_de_donnee"],
                    date_extraction=date.fromisoformat(extraction) if extraction else None,
                    traitements=row["traitements"],
                    limites=row["limites"],
                    licence=row["licence"],
                    statut=row["statut"],
                )
        return cls(records)

    def get(self, source_id: str) -> SourceRecord:
        try:
            return self._records[source_id]
        except KeyError:
            raise KeyError(f"Source absente du registre : {source_id}") from None

    def require_used(self, source_id: str) -> SourceRecord:
        record = self.get(source_id)
        if record.statut != STATUT_UTILISE:
            raise ValueError(f"Source {source_id} non utilisable (statut « {record.statut} »)")
        return record

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._records
