"""Assemble contraintes et scores : classement, rejets, « aucune recommandation », confiance.

Conception : docs/03_DECISION_ENGINE.md (sections « Aucune recommandation » et « Rôle du débat »)
Le moteur est déterministe et n'appelle aucun LLM. Le débat (P3) viendra enrichir `confidence`
et `disagreements` ; ici la confiance se fonde sur la couverture des données.

« Aucune recommandation » est renvoyée quand :
- aucun actif ne passe les contraintes dures ;
- preuves insuffisantes (tous les candidats ont un score d'adéquation nul) ;
- confiance faible sur tous les candidats (trop de poids sur des critères non sourcés).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from easytrade.data.point_in_time import DateLike, to_timestamp
from easytrade.engine.constraints import screen_assets
from easytrade.engine.scoring import score_candidates
from easytrade.schemas.decision import Confidence, Decision
from easytrade.schemas.weights import CRITERIA, ProfileWeights

# Libellés lisibles des critères non couverts, pour « ce que nous ne savons pas ».
MISSING_LABELS = {
    "esg": "signaux ESG non encore sourcés",
    "qualite": "fondamentaux (qualité) non encore sourcés",
    "preferences": "correspondance aux préférences déclarées non encore modélisée",
    "croissance": "historique de prix insuffisant",
    "stabilite": "historique de prix insuffisant",
    "horizon": "historique de prix insuffisant",
    "diversification": "apport à la diversification indisponible",
}

CONFIDENCE_LOW = 0.40   # poids manquant au-delà duquel la confiance est faible
CONFIDENCE_MID = 0.20   # ... au-delà duquel elle est moyenne


def _confidence(missing_weight: float) -> Confidence:
    if missing_weight >= CONFIDENCE_LOW:
        return "faible"
    if missing_weight >= CONFIDENCE_MID:
        return "moyen"
    return "élevé"


def decide(
    assets: pd.DataFrame,
    signals: dict[str, dict[str, Optional[float]]],
    evidence: dict[str, dict[str, Optional[str]]],
    profile_weights: ProfileWeights,
    as_of: DateLike,
    *,
    esg_controversial: frozenset[str] = frozenset(),
) -> Decision:
    """Produit la décision pour un persona sur un univers donné."""
    as_of_date = to_timestamp(as_of).date()
    weights = profile_weights.weights
    screening = screen_assets(assets, profile_weights.constraints, esg_controversial)

    if not screening.eligible:
        return Decision(
            as_of=as_of_date,
            persona_id=profile_weights.persona_id,
            ranking=(),
            rejected=screening.rejected,
            no_recommendation=True,
            reason="Aucun actif de l'univers ne passe les contraintes dures de votre profil.",
            confidence="faible",
        )

    ranking = score_candidates(
        screening.eligible, signals, evidence, weights, screening.flags
    )

    # Critères manquants pour *tous* les candidats retenus → poids manquant global.
    missing_for_all = [
        criterion for criterion in CRITERIA
        if all(criterion in candidate.missing_criteria for candidate in ranking)
    ]
    missing_weight = sum(float(weights[c]) for c in missing_for_all)
    confidence = _confidence(missing_weight)
    missing_info = tuple(MISSING_LABELS.get(c, c) for c in missing_for_all)

    all_scores_null = all(candidate.fit_score == 0.0 for candidate in ranking)
    no_recommendation = all_scores_null or confidence == "faible"
    if all_scores_null:
        reason = "Preuves insuffisantes : aucun critère exploitable sur les actifs admissibles."
    elif confidence == "faible":
        reason = (
            "Confiance trop faible pour recommander : trop de poids de votre profil porte sur "
            "des critères non encore sourcés (" + ", ".join(missing_info) + ")."
        )
    else:
        reason = ""

    return Decision(
        as_of=as_of_date,
        persona_id=profile_weights.persona_id,
        ranking=tuple(ranking),
        rejected=screening.rejected,
        no_recommendation=no_recommendation,
        reason=reason,
        missing_info=missing_info,
        confidence=confidence,
    )
