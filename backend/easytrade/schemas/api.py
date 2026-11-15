"""Contrats de réponse de l'API HTTP : ce que le mobile reçoit.

Conception : docs/01_ARCHITECTURE.md (API), mobile/src/types/contracts.ts
Miroir Pydantic de `mobile/src/types/contracts.ts` pour tout ce qui n'est pas déjà un schéma du
pipeline (`Explanation`, `RunTrace`, `Evidence` sont servis tels quels). Les schémas internes du
moteur (`ProfileWeights`, `Decision`, `CoherenceReport`) gardent leur forme : la couche API
(`api/presenters.py`) les traduit vers ces contrats de présentation.

La conformité est testée des deux côtés contre un seul schéma JSON, généré depuis
`contracts.ts` : `mobile/contracts.schema.json` (backend/tests/api/, mobile/tests/).
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from easytrade.schemas.debate import Claim
from easytrade.schemas.evidence import ClaimKind
from easytrade.schemas.explanation import Explanation
from easytrade.schemas.weights import Speculatif

# --- profil -----------------------------------------------------------------------------------
Objectif = Literal["preserver", "equilibre", "croissance"]
HorizonChoice = Literal["court", "moyen", "long"]
ToleranceChoice = Literal["faible", "moderee", "elevee"]


class ProfileDraft(BaseModel):
    """Corps de `POST /profiles` : réponses du questionnaire, ou poids modifiés d'un profil existant."""

    model_config = ConfigDict(extra="forbid")

    objectif: Objectif = "equilibre"
    horizon: HorizonChoice = "moyen"
    tolerance: ToleranceChoice = "moderee"
    preferences: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    weights_override: Optional[dict[str, float]] = None
    base_persona: Optional[str] = None


class HardConstraintsView(BaseModel):
    max_weight_per_asset: float
    max_weight_per_sector: float
    max_weight_crypto: float
    excluded_asset_classes: list[str] = Field(default_factory=list)
    esg_exclusion: bool = False
    speculatif: Speculatif = "permis"


class RationaleView(BaseModel):
    field: str
    because: str
    claim_kind: ClaimKind = "HYPOTHESE"


class ProfileWeightsView(BaseModel):
    """`ProfileWeights` tel qu'affiché : « Voici comment nous avons compris votre profil »."""

    profile_id: str
    label: str
    summary: str
    hard_constraints: HardConstraintsView
    weights: dict[str, float]
    rationale: list[RationaleView] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


# --- exécution --------------------------------------------------------------------------------
RunStepId = Literal["profil", "recherche_validation", "debat", "decision", "explication"]
RunStepStatus = Literal["attente", "en_cours", "ok", "echec"]
RunState = Literal["en_cours", "termine", "echec"]
RUN_STEPS: tuple[str, ...] = ("profil", "recherche_validation", "debat", "decision", "explication")


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    as_of: Optional[date] = None
    requested_ticker: Optional[str] = None


class RunCreated(BaseModel):
    run_id: str


class RunStepView(BaseModel):
    id: RunStepId
    status: RunStepStatus


class RunStatusView(BaseModel):
    """Réponse de `GET /runs/{id}` : état, étapes affichées, résultat une fois terminé."""

    run_id: str
    profile_id: str
    as_of: date
    requested_ticker: Optional[str] = None
    status: RunState
    steps: list[RunStepView]
    error: Optional[str] = None
    result: Optional[Explanation] = None


# --- actifs -----------------------------------------------------------------------------------
class AssetSummary(BaseModel):
    ticker: str
    name: str
    asset_class: str
    sector: Optional[str] = None
    currency: str


class AssetMetricView(BaseModel):
    metric: str
    label: str
    value: float
    unit: str
    window: str
    evidence_id: str
    universe_min: float
    universe_max: float
    profile_limit: Optional[float] = None  # repère indicatif du profil (hypothèse de l'équipe)
    advanced: bool = False


class AssetSheet(AssetSummary):
    as_of: date
    metrics: list[AssetMetricView] = Field(default_factory=list)
    signals: list[Claim] = Field(default_factory=list)


# --- graphe -----------------------------------------------------------------------------------
Relation = Literal["FOURNISSEUR", "CLIENT", "CONCURRENT", "PARTENAIRE"]


class GraphNode(BaseModel):
    id: str
    label: str
    in_universe: bool


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: Relation
    claim_kind: Literal["FAIT", "HYPOTHESE"]
    evidence_id: Optional[str] = None


class DependencyGraph(BaseModel):
    center: str
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)


# --- données ----------------------------------------------------------------------------------
class SourceInfo(BaseModel):
    source_id: str
    nom: str
    type_de_donnee: str
    date_extraction: Optional[date] = None
    limites: str
    statut: str


class QualityCheck(BaseModel):
    check: str
    status: Literal["ok", "avertissement", "erreur"]
    details: list[str] = Field(default_factory=list)


class DataOverview(BaseModel):
    as_of: date
    sources: list[SourceInfo]
    quality: list[QualityCheck]
