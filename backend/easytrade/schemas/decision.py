"""Decision : classement, rejets motivés, informations manquantes, ou « aucune recommandation ».

Conception : docs/03_DECISION_ENGINE.md
« Aucune recommandation » est une sortie valide et attendue, pas une erreur.
Le débat (agents) ne modifie pas le score : il alimente `confidence` et `disagreements`,
remplis à l'étape P3. Le moteur seul produit un niveau de confiance fondé sur la couverture
des données.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from easytrade.schemas.candidate import Rejection, ScoredCandidate

Confidence = Literal["élevé", "moyen", "faible"]


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    persona_id: str
    ranking: tuple[ScoredCandidate, ...] = ()
    rejected: tuple[Rejection, ...] = ()
    no_recommendation: bool = False
    reason: str = ""                          # pourquoi aucune reco / réserves
    missing_info: tuple[str, ...] = ()
    confidence: Confidence = "moyen"
    disagreements: tuple[str, ...] = ()       # recopiés du débat (P3), vides ici
