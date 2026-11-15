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
    disagreements: tuple[str, ...] = ()       # recopiés tels quels du débat (engine.decision.apply_debate)
    # --- remplis après le débat et les garde-fous de panier (P3) ---
    retained: tuple[str, ...] = ()            # pistes retenues, dans l'ordre du classement
    displaced: tuple[Rejection, ...] = ()     # déclassés par un garde-fou de panier (concentration)
    candidate_confidence: dict[str, Confidence] = {}  # par piste : couverture des données + accord du débat
    to_review: tuple[str, ...] = ()           # drapeau « à examiner » (opposition du Bear liée au profil)
