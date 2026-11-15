"""Assemble contraintes et scores : classement, rejets, « aucune recommandation », confiance.

Conception : docs/03_DECISION_ENGINE.md (sections « Aucune recommandation » et « Rôle du débat »)
Le moteur est déterministe et n'appelle aucun LLM. Le débat (P3) viendra enrichir `confidence`
et `disagreements` ; ici la confiance se fonde sur la couverture des données.

« Aucune recommandation » est renvoyée quand :
- aucun actif ne passe les contraintes dures ;
- preuves insuffisantes (tous les candidats ont un score d'adéquation nul) ;
- confiance faible sur tous les candidats (trop de poids sur des critères non sourcés).

Le critère le plus important du profil sans aucune donnée sur les candidats ne bloque plus (décision de
l'équipe, 2026-11-15) : les pistes sont classées sur les autres critères, un avertissement le dit en tête,
et chaque piste à qui manque ce critère a une confiance « faible » (`apply_debate`).
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

import pandas as pd

from easytrade.data.point_in_time import DateLike, to_timestamp
from easytrade.engine.constraints import screen_assets
from easytrade.engine.esg import ESG_FOCUS_WEIGHT
from easytrade.engine.scoring import score_candidates
from easytrade.schemas.debate import AGENT_LABELS, STANCE_LABELS, DebateRecord
from easytrade.schemas.decision import Confidence, Decision
from easytrade.schemas.weights import CRITERIA, CRITERION_LABELS, ProfileWeights

# Libellés lisibles des critères non couverts, pour « ce que nous ne savons pas ».
MISSING_LABELS = {
    "esg": "aucune preuve ESG concluante à cette date",
    "qualite": "fondamentaux (qualité) non publiés à cette date",
    "preferences": "correspondance aux préférences déclarées non encore modélisée",
    "croissance": "historique de prix insuffisant",
    "stabilite": "historique de prix insuffisant",
    "horizon": "historique de prix insuffisant",
    "diversification": "apport à la diversification indisponible",
}

def esg_focused(weights: Mapping[str, float]) -> bool:
    """Profil qui accorde une grande importance à l'ESG (poids d'au moins `ESG_FOCUS_WEIGHT`)."""
    return float(weights.get("esg", 0.0)) >= ESG_FOCUS_WEIGHT - 1e-6  # poids arrondis à 6 décimales


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
    esg_emitters: frozenset[str] = frozenset(),
    candidates: Optional[Iterable[str]] = None,
    risk: Optional[Mapping[str, tuple[Optional[float], Optional[float]]]] = None,
    risk_level: Optional[str] = None,
) -> Decision:
    """Produit la décision pour un persona sur un univers donné.

    `candidates` (P3) : si fourni, seuls ces tickers sont classés. Les scores restent normalisés
    sur tout l'univers admissible : le choix des candidats par l'agent de recherche ne change pas
    le score d'un actif.
    `risk` (ticker → (volatilité %, perte maximale %)) et `risk_level` : règle de tolérance au risque
    (`engine.constraints`) ; le pipeline les fournit toujours.
    """
    as_of_date = to_timestamp(as_of).date()
    weights = profile_weights.weights
    screening = screen_assets(assets, profile_weights.constraints, esg_controversial,
                              esg_emitters=esg_emitters, esg_focus=esg_focused(weights),
                              risk=risk, risk_level=risk_level)

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

    # Critère prioritaire du profil (poids le plus élevé) sans aucune donnée sur les candidats : avertissement
    # (décision de l'équipe, 2026-11-15 ; ex. un profil « ESG seulement » sans titre ESG prouvé admissible).
    top_weight = max(float(w) for w in weights.values())
    top_missing = [c for c in missing_for_all if float(weights[c]) == top_weight]

    all_scores_null = all(candidate.fit_score == 0.0 for candidate in ranking)
    # Critère prioritaire sans donnée : pistes classées sur les autres critères, avec avertissement. Ce n'est
    # pas la confiance commune « faible » qui doit alors bloquer : elle vient précisément de ce critère.
    no_recommendation = all_scores_null or (confidence == "faible" and not top_missing)
    warnings: tuple[str, ...] = ()
    if top_missing and not all_scores_null:
        criterion = top_missing[0]
        warnings = (
            f"Avertissement : aucune piste admissible n'a de donnée pour le critère le plus important de votre "
            f"profil ({CRITERION_LABELS.get(criterion, criterion)}, {top_weight * 100:.0f} %) : "
            f"{MISSING_LABELS.get(criterion, criterion)}. Les pistes sont classées sur vos autres critères : elles "
            f"ne répondent pas à ce critère et leur confiance est faible.",
        )
    if all_scores_null:
        reason = "Preuves insuffisantes : aucun critère exploitable sur les actifs admissibles."
    elif no_recommendation:
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
        warnings=warnings,
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
    données et celle tirée du débat. La couverture est celle **de la piste** : le poids des critères
    qui lui manquent (une piste sans preuve ESG pour un profil qui pèse l'ESG à 25 % n'est pas
    « élevée »), jamais meilleure que la couverture commune (`decision.confidence`). Une piste non
    débattue garde la confiance des données. Les désaccords sont recopiés tels quels.
    """
    records = list(records)
    by_ticker = {record.ticker: record for record in records}
    common_level = _LEVELS.index(decision.confidence)
    confidence: dict[str, Confidence] = {}
    for candidate in decision.ranking:
        own_missing = sum(c.weight for c in candidate.criteria if c.missing)
        data_level = min(common_level, _LEVELS.index(_confidence(own_missing)))
        # Piste sans le critère le plus important du profil : confiance faible (elle ne répond pas à ce critère).
        top_weight = max((c.weight for c in candidate.criteria), default=0.0)
        if any(c.missing and c.weight == top_weight for c in candidate.criteria):
            data_level = 0
        record = by_ticker.get(candidate.ticker)
        level = data_level if record is None else min(data_level, _LEVELS.index(debate_confidence(record)))
        confidence[candidate.ticker] = _LEVELS[level]
    profile_ids = tuple(profile_evidence_ids)
    return decision.model_copy(update={
        "candidate_confidence": confidence,
        "disagreements": tuple(_disagreement(record) for record in records if record.dissent),
        "to_review": tuple(record.ticker for record in records if bear_flags_profile(record, profile_ids)),
    })
