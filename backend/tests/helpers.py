"""Aides de test : petit registre de preuves fictif (aucune donnée de marché réelle)."""
from datetime import date

from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.schemas.evidence import EvidenceDraft, EvidenceSource, EvidenceWindow

AS_OF = date(2026, 11, 12)
SOURCE = EvidenceSource(source_id="test", name="Source de test")


def draft(statement, value=None, unit="%", claim_kind="FAIT", evidence_type="metric", subject="AAA",
          published_at=AS_OF, window=None):
    return EvidenceDraft(
        type=evidence_type, claim_kind=claim_kind, subject=subject, statement=statement, value=value, unit=unit,
        window=window or EvidenceWindow(), observed_at=published_at, published_at=published_at, source=SOURCE,
        processing="test", produced_by="tests.helpers@v1",
    )


def sample_ledger():
    """Registre témoin. Identifiants : EV-000001 volatilité 35,24 % ; EV-000002 perte maximale -41,6 % ;
    EV-000003 pire période glissante de 3 ans -12,0 % ; EV-000004 repère (HYPOTHESE) 25 % ;
    EV-000005 panier simulé (SCENARIO) 9,8 % ; EV-000006 phrase de profil sans valeur."""
    ledger = EvidenceLedger(AS_OF)
    ledger.add(draft("Volatilité annualisée (toute la période, CAD)", 35.24))
    ledger.add(draft("Perte maximale sur la fenêtre observée (toute la période, CAD)", -41.6))
    ledger.add(draft("Pire période glissante de 3 ans (toute la période, CAD)", -12.0))
    ledger.add(draft("Repère de volatilité annualisée pour une tolérance au risque modérée", 25.0,
                     claim_kind="HYPOTHESE", evidence_type="profile"))
    ledger.add(draft("Volatilité annualisée d'un panier simulé (10 pistes retenues, parts égales)", 9.8,
                     claim_kind="SCENARIO"))
    ledger.add(draft("Préférence déclarée : souhaite garder une diversification", None, unit=None,
                     evidence_type="profile"))
    return ledger
