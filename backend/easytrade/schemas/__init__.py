"""Contrats Pydantic échangés entre les étapes du pipeline.

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md
Point d'import unique pour les schémas stables du moteur (P2) et des agents (P3).
"""
from easytrade.schemas.candidate import (
    Asset,
    Candidate,
    CandidateList,
    CriterionScore,
    EvidencePack,
    Rejection,
    ScoredCandidate,
)
from easytrade.schemas.coherence import CoherenceReport, Tension, Verdict
from easytrade.schemas.debate import Claim, DebateRecord, DebateTurn
from easytrade.schemas.decision import Confidence, Decision
from easytrade.schemas.evidence import Evidence, EvidenceDraft
from easytrade.schemas.explanation import (
    CoherenceAnalysis,
    Explanation,
    ExplanationItem,
    RejectedItem,
)
from easytrade.schemas.metrics import MetricResult
from easytrade.schemas.profile import HorizonYears, Profile
from easytrade.schemas.trace import RunTrace, TraceStep
from easytrade.schemas.weights import CRITERIA, HardConstraints, ProfileWeights

__all__ = [
    "Asset",
    "Candidate",
    "CandidateList",
    "CriterionScore",
    "EvidencePack",
    "Rejection",
    "ScoredCandidate",
    "CoherenceReport",
    "Tension",
    "Verdict",
    "Claim",
    "DebateRecord",
    "DebateTurn",
    "Confidence",
    "Decision",
    "Evidence",
    "EvidenceDraft",
    "CoherenceAnalysis",
    "Explanation",
    "ExplanationItem",
    "RejectedItem",
    "MetricResult",
    "HorizonYears",
    "Profile",
    "RunTrace",
    "TraceStep",
    "CRITERIA",
    "HardConstraints",
    "ProfileWeights",
]
