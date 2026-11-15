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

from typing import Iterable, Optional

import pandas as pd

from easytrade.data.point_in_time import DateLike, to_timestamp
from easytrade.engine.constraints import screen_assets
from easytrade.engine.scoring import score_candidates
from easytrade.schemas.debate import AGENT_LABELS, STANCE_LABELS, DebateRecord
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
    candidates: Optional[Iterable[str]] = None,
) -> Decision:
    """Produit la décision pour un persona sur un univers donné.

    `candidates` (P3) : si fourni, seuls ces tickers sont classés. Les scores restent normalisés
    sur tout l'univers admissible : le choix des candidats par l'agent de recherche ne change pas
    le score d'un actif.
    """
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
    if candidates is not None:
        wanted = set(candidates)
        ranking = [candidate for candidate in ranking if candidate.ticker in wanted]
    if not ranking:
        return Decision(
            as_of=as_of_date,
            persona_id=profile_weights.persona_id,
            ranking=(),
            rejected=screening.rejected,
            no_recommendation=True,
            reason="Preuves insuffisantes : aucun candidat admissible à classer.",
            confidence="faible",
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


# --- prise en compte du débat (P3) --------------------------------------------------------------
_LEVELS: tuple[Confidence, ...] = ("faible", "moyen", "élevé")


def debate_confidence(record: DebateRecord) -> Confidence:
    """Confiance tirée de l'accord des trois positions finales (docs/03, « Rôle du débat »).

    - trois appuis sans réserve : élevé ;
    - au moins deux oppositions, ou aucune position : faible ;
    - tout le reste (réserves, une opposition) : moyen.
    """
    stances = list(record.stances.values())
    if not stances or sum(1 for s in stances if s == "opposition") >= 2:
        return "faible"
    if all(s == "appui" for s in stances):
        return "élevé"
    return "moyen"


def _disagreement(record: DebateRecord) -> str:
    parts = []
    for turn in record.final:
        first = turn.arguments[0].text if turn.arguments else "aucun argument étayé retenu"
        parts.append(f"{AGENT_LABELS[turn.agent]} : {STANCE_LABELS[turn.stance]} ({first})")
    return f"{record.ticker} — " + " ; ".join(parts)


def bear_flags_profile(record: DebateRecord, profile_evidence_ids: Iterable[str]) -> bool:
    """Opposition du Bear appuyée sur un argument qui cite une preuve du profil (règle, repère)."""
    bear = record.position("bear")
    if bear is None or bear.stance != "opposition":
        return False
    profile_ids = set(profile_evidence_ids)
    return any(profile_ids.intersection(argument.evidence_ids) for argument in bear.arguments)


def apply_debate(
    decision: Decision,
    records: Iterable[DebateRecord],
    *,
    profile_evidence_ids: Iterable[str] = (),
) -> Decision:
    """Intègre le débat sans toucher aux scores : confiance par piste, désaccords, drapeaux.

    La confiance d'une piste est le minimum entre la confiance fondée sur la couverture des
    données (`decision.confidence`) et celle tirée du débat. Une piste non débattue garde la
    confiance des données. Les désaccords sont recopiés tels quels.
    """
    records = list(records)
    by_ticker = {record.ticker: record for record in records}
    data_level = _LEVELS.index(decision.confidence)
    confidence: dict[str, Confidence] = {}
    for candidate in decision.ranking:
        record = by_ticker.get(candidate.ticker)
        level = data_level if record is None else min(data_level, _LEVELS.index(debate_confidence(record)))
        confidence[candidate.ticker] = _LEVELS[level]
    profile_ids = tuple(profile_evidence_ids)
    return decision.model_copy(update={
        "candidate_confidence": confidence,
        "disagreements": tuple(_disagreement(record) for record in records if record.dissent),
        "to_review": tuple(record.ticker for record in records if bear_flags_profile(record, profile_ids)),
    })
