"""CoherenceReport : analyse de cohérence d'un titre soumis par l'utilisateur (« Tester une idée »).

Conception : docs/03_DECISION_ENGINE.md (section « Demande explicite de l'utilisateur »)
Réponse au test Robert : relever la tension, expliquer le risque, ne pas acquiescer.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

Verdict = Literal["cohérent", "cohérent avec réserve", "incohérent avec le profil"]


class Tension(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension: str                 # ex. « volatilité », « horizon », « contrainte »
    detail: str                    # explication chiffrée et lisible
    severe: bool = False           # une tension sévère suffit à bloquer un « cohérent »
    evidence_id: Optional[str] = None
    evidence_ids: tuple[str, ...] = ()  # preuves supplémentaires (repère du profil, médiane de référence)


class CoherenceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    verdict: Verdict
    tensions: tuple[Tension, ...] = ()
    context: str = ""              # effet sur le panier simulé
    alternatives: tuple[str, ...] = ()  # tickers répondant au même intérêt avec moins de tension
