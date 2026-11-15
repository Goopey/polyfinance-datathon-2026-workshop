"""Explanation : sortie finale affichée par le mobile.

Conception : docs/02_AGENTS.md (section 5)
Miroir Pydantic de `mobile/src/types/contracts.ts` : mêmes noms de champs, mêmes valeurs.
Tout texte qui affirme quelque chose est un `Claim` (texte + preuves) ; les listes de chaînes
(`risks`, `limits`, `unknowns`) sont composées par le code à partir d'éléments déjà vérifiés.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from easytrade.schemas.coherence import Verdict
from easytrade.schemas.debate import AgentConfidence, Claim, DebateAgent, Stance

Fit = Literal["élevée", "partielle", "faible"]
RejectionKind = Literal["contrainte", "classement", "preuves"]

DISCLAIMER = "Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier."


class DebatePosition(BaseModel):
    """Position finale d'un agent (tour 3)."""

    model_config = ConfigDict(frozen=True)

    agent: DebateAgent
    stance: Stance
    confidence: AgentConfidence
    arguments: tuple[Claim, ...] = ()
    open_questions: tuple[str, ...] = ()


class DebateSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    bull: str
    realist: str
    bear: str
    dissent: bool


class ExplanationItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    asset_class: str
    sector: Optional[str] = None
    fit: Fit
    confidence: AgentConfidence
    to_review: bool = False
    why: tuple[Claim, ...] = ()
    contributions: dict[str, float] = Field(default_factory=dict)
    not_applicable: tuple[str, ...] = ()  # critères sans objet pour ce type d'actif (ex. qualité d'un FNB) : poids réparti
    debate: tuple[DebatePosition, ...] = ()
    debate_summary: DebateSummary
    risks: tuple[str, ...] = ()
    limits: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


class RejectedItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    reason: str
    kind: RejectionKind
    evidence_ids: tuple[str, ...] = ()


class Alternative(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    why: Claim


class CoherenceAnalysis(BaseModel):
    """« Tester une idée » : verdict, tensions chiffrées, effet sur le panier simulé, alternatives."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    verdict: Verdict
    tensions: tuple[Claim, ...] = ()
    context: tuple[Claim, ...] = ()
    alternatives: tuple[Alternative, ...] = ()


class Explanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    as_of: date
    profile_id: str
    headline: str
    no_recommendation: bool = False
    missing: tuple[str, ...] = ()
    items: tuple[ExplanationItem, ...] = ()
    rejected: tuple[RejectedItem, ...] = ()
    coherence: Optional[CoherenceAnalysis] = None
    unknowns: tuple[str, ...] = ()
    disclaimer: str = DISCLAIMER


# --- sortie brute de l'agent d'explication (avant vérification de fidélité) -------------------
class ItemDraft(BaseModel):
    ticker: str
    why: list[Claim] = Field(default_factory=list)


class ExplanationDraft(BaseModel):
    items: list[ItemDraft] = Field(default_factory=list)
    coherence_notes: list[Claim] = Field(default_factory=list)
