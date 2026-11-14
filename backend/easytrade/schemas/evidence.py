"""Evidence : preuve identifiée (type, claim_kind, valeur, fenêtre, trois dates, source, traitement, limites).

Conception : docs/05_EXPLICABILITE.md
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

EvidenceType = Literal["metric", "filing", "esg", "relation", "macro", "news", "profile"]
ClaimKind = Literal["FAIT", "HYPOTHESE", "SCENARIO"]


class EvidenceWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: Optional[date] = None
    end: Optional[date] = None
    observations: Optional[int] = None


class EvidenceSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    name: str
    url: Optional[str] = None


class EvidenceDraft(BaseModel):
    """Preuve sans identifiant. Le registre attribue `evidence_id`."""

    model_config = ConfigDict(frozen=True)

    type: EvidenceType
    claim_kind: ClaimKind = "FAIT"
    subject: str
    statement: str
    value: Optional[float] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    window: EvidenceWindow = EvidenceWindow()
    observed_at: date
    published_at: date
    retrieved_at: Optional[date] = None
    source: EvidenceSource
    processing: str
    produced_by: str
    limits: str = ""


class Evidence(EvidenceDraft):
    evidence_id: str
