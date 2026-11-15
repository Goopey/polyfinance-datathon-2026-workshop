"""RunTrace : étapes observables d'une exécution.

Conception : docs/05_EXPLICABILITE.md (section 3)
On enregistre ce qui a été fait (entrées, outils appelés, sorties, modèle, statut), jamais le
raisonnement interne d'un modèle. `kind` : `code` (Python déterministe), `llm` (appel de modèle),
`controle` (point de contrôle de gouvernance, docs/08_CONFORMITE.md).
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

StepKind = Literal["code", "llm", "controle"]
StepStatus = Literal["ok", "echec", "ignore"]


class TraceStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: str
    kind: StepKind
    status: StepStatus = "ok"
    started_at: str
    ended_at: str
    model_id: Optional[str] = None
    prompt_version: Optional[str] = None
    version: Optional[str] = None
    attempts: Optional[int] = None  # appels au modèle (2 = une relance après sortie invalide)
    tools_called: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    evidence_in: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    note: str = ""


class RunTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    as_of: date
    profile_id: str
    steps: tuple[TraceStep, ...] = ()
