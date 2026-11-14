"""Registre de preuves : identifiants stables, déduplication, refus des preuves futures."""
from datetime import date

import pytest

from easytrade.explain.evidence_ledger import EvidenceLedger, FutureEvidenceError
from easytrade.schemas.evidence import EvidenceDraft, EvidenceSource


def _draft(value=1.0, published=date(2024, 1, 2)):
    return EvidenceDraft(
        type="metric", subject="AAA", statement="Test", value=value, unit="%", observed_at=published,
        published_at=published, source=EvidenceSource(source_id="starter_prices", name="Yahoo"),
        processing="test", produced_by="test@v1",
    )


def test_identifiants_sequentiels_et_deduplication():
    ledger = EvidenceLedger(date(2024, 1, 31))
    a = ledger.add(_draft(1.0))
    b = ledger.add(_draft(2.0))
    again = ledger.add(_draft(1.0))
    assert (a.evidence_id, b.evidence_id) == ("EV-000001", "EV-000002")
    assert again.evidence_id == a.evidence_id and len(ledger) == 2
    assert ledger.get("EV-000002").value == 2.0 and "EV-000001" in ledger


def test_preuve_future_refusee():
    ledger = EvidenceLedger(date(2024, 1, 31))
    with pytest.raises(FutureEvidenceError):
        ledger.add(_draft(published=date(2024, 2, 1)))
    assert len(ledger) == 0


def test_preuve_inconnue():
    with pytest.raises(KeyError):
        EvidenceLedger(date(2024, 1, 31)).get("EV-000099")
