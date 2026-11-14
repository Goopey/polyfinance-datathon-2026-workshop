"""Contrats Pydantic échangés entre les étapes du pipeline.

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md
Point d'import unique pour les schémas stables du moteur (P2).
"""
from easytrade.schemas.candidate import (
    Asset,
    CriterionScore,
    Rejection,
    ScoredCandidate,
)
from easytrade.schemas.coherence import CoherenceReport, Tension, Verdict
from easytrade.schemas.decision import Confidence, Decision
from easytrade.schemas.evidence import Evidence, EvidenceDraft
from easytrade.schemas.metrics import MetricResult
from easytrade.schemas.profile import HorizonYears, Profile
from easytrade.schemas.weights import CRITERIA, HardConstraints, ProfileWeights

__all__ = [
    "Asset",
    "CriterionScore",
    "Rejection",
    "ScoredCandidate",
    "CoherenceReport",
    "Tension",
    "Verdict",
    "Confidence",
    "Decision",
    "Evidence",
    "EvidenceDraft",
    "MetricResult",
    "HorizonYears",
    "Profile",
    "CRITERIA",
    "HardConstraints",
    "ProfileWeights",
]
