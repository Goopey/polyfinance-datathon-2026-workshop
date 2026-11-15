"""Débat : affirmation sourcée, tour d'un agent, dossier du débat par candidat.

Conception : docs/02_AGENTS.md (section 3)
- `Claim` : affirmation courte, toujours rattachée à des preuves (`evidence_ids`).
- `DebateTurnDraft` : ce que le modèle renvoie (schéma de sortie structurée).
- `DebateTurn` : le tour validé par le code (arguments sans preuve valide supprimés).
- `DebateRecord` : tours 1 et 3 des trois agents pour un candidat ; la dissidence est conservée.
Les niveaux de confiance des agents sont au féminin (« élevée »), comme dans docs/02_AGENTS.md
et le contrat mobile ; le moteur (`Decision`) garde ses valeurs propres.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from easytrade.schemas.evidence import ClaimKind

Stance = Literal["appui", "appui_reserve", "opposition"]
AgentConfidence = Literal["élevée", "moyenne", "faible"]
DebateAgent = Literal["bull", "realist", "bear"]

AGENTS: tuple[str, ...] = ("bull", "realist", "bear")
AGENT_LABELS = {"bull": "Bull", "realist": "Réaliste", "bear": "Bear"}
STANCE_LABELS = {"appui": "appui", "appui_reserve": "appui avec réserve", "opposition": "opposition"}


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    evidence_ids: tuple[str, ...] = ()
    claim_kind: ClaimKind = "FAIT"


class DebateTurnDraft(BaseModel):
    """Sortie brute d'un agent du débat (avant contrôle par le code)."""

    stance: Stance
    confidence: AgentConfidence = "moyenne"
    arguments: list[Claim] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class DebateTurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    agent: DebateAgent
    round: Literal[1, 3]
    stance: Stance
    confidence: AgentConfidence
    arguments: tuple[Claim, ...] = ()
    open_questions: tuple[str, ...] = ()
    removed_arguments: int = 0  # arguments supprimés par le code (preuve absente, nombre non étayé)


class DebateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    round1: tuple[DebateTurn, ...] = ()
    final: tuple[DebateTurn, ...] = ()

    def position(self, agent: str) -> Optional[DebateTurn]:
        return next((turn for turn in self.final if turn.agent == agent), None)

    @property
    def stances(self) -> dict[str, str]:
        return {turn.agent: turn.stance for turn in self.final}

    @property
    def dissent(self) -> bool:
        """Désaccord : au moins un agent s'oppose pendant qu'un autre ne s'oppose pas.

        Une simple réserve (« appui avec réserve ») à côté d'appuis n'est pas un désaccord : l'afficher
        comme tel sur presque toutes les pistes viderait le signal de son sens (audit H2)."""
        stances = set(self.stances.values())
        return "opposition" in stances and len(stances) > 1

    @property
    def removed_arguments(self) -> int:
        return sum(turn.removed_arguments for turn in (*self.round1, *self.final))
