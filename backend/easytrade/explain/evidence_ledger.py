"""Registre de preuves : création, identifiants, lecture.

Conception : docs/05_EXPLICABILITE.md
Les identifiants (`EV-000001`, ...) suivent l'ordre d'insertion : deux exécutions identiques
produisent les mêmes identifiants. Une preuve identique à une preuve existante est réutilisée.
Une preuve dont `published_at` dépasse `as_of` est refusée (scénario S5).
"""
from __future__ import annotations

from datetime import date
from typing import Iterator

from easytrade.schemas.evidence import Evidence, EvidenceDraft


class FutureEvidenceError(ValueError):
    """Preuve publiée après la date de référence de l'analyse."""


class EvidenceLedger:
    def __init__(self, as_of: date):
        self.as_of = as_of
        self._items: dict[str, Evidence] = {}
        self._by_content: dict[str, str] = {}

    def add(self, draft: EvidenceDraft) -> Evidence:
        if draft.published_at > self.as_of:
            raise FutureEvidenceError(
                f"Preuve publiée le {draft.published_at} après as_of={self.as_of} : {draft.statement}"
            )
        key = draft.model_dump_json()
        existing = self._by_content.get(key)
        if existing is not None:
            return self._items[existing]
        evidence_id = f"EV-{len(self._items) + 1:06d}"
        evidence = Evidence(evidence_id=evidence_id, **draft.model_dump())
        self._items[evidence_id] = evidence
        self._by_content[key] = evidence_id
        return evidence

    def get(self, evidence_id: str) -> Evidence:
        try:
            return self._items[evidence_id]
        except KeyError:
            raise KeyError(f"Preuve inconnue : {evidence_id}") from None

    def __contains__(self, evidence_id: str) -> bool:
        return evidence_id in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Evidence]:
        return iter(self._items.values())

    def ids(self) -> list[str]:
        return list(self._items)

    def to_records(self) -> list[dict]:
        return [e.model_dump(mode="json") for e in self]
