"""Agent 1 : profil → ProfileWeights (contraintes dures, poids, thèmes, justification, informations manquantes).

Conception : docs/02_AGENTS.md (section 1), docs/03_DECISION_ENGINE.md
Pourquoi il existe : transformer un profil exprimé en langage courant en paramètres que le
moteur peut appliquer, et rendre ce passage visible.

Partage des rôles :
- le modèle lit le profil, propose des poids, des resserrements de règles, des thèmes d'intérêt
  (vocabulaire fermé) et la justification de chaque valeur, rattachée à une phrase du profil ;
- le code part d'un **gabarit** (le persona, ou le gabarit du niveau de risque), borne chaque
  poids à ± `MAX_WEIGHT_SHIFT` autour du gabarit, renormalise, et n'accepte qu'un
  **resserrement** des contraintes dures : un modèle ne peut pas assouplir une règle.
Chaque phrase du profil devient une preuve `FAIT` (type `profile`) ; chaque poids, plafond et
repère de risque devient une preuve `HYPOTHESE` : ce sont des choix de l'équipe, affichés tels.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from easytrade.agents.llm_client import TIER_STRONG, CallInfo, LLMClient, load_prompt, structured_call
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.engine.coherence import RISK_LIMITS, tolerance_level
from easytrade.engine.signals import THEMES
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.fidelity import check_claim
from easytrade.schemas.debate import Claim
from easytrade.schemas.evidence import ClaimKind, EvidenceDraft
from easytrade.schemas.profile import Profile
from easytrade.schemas.weights import CRITERIA, CRITERION_LABELS, HardConstraints, ProfileWeights

STEP = "profile_weighting"
VERSION = "v1"
SOURCE_PROFILE = "case_personas"
SOURCE_HYPOTHESES = "easytrade_hypotheses"
MAX_WEIGHT_SHIFT = 0.10  # écart maximal d'un poids par rapport au gabarit (hypothèse de l'équipe)
TEMPLATE_BY_LEVEL = {"faible": "robert", "faible à modérée": "robert", "modérée": "mateo", "élevée": "amira"}
_SPECULATIF_ORDER = ("permis", "signalé", "exclu")  # du plus souple au plus strict

CONSTRAINT_LABELS = {
    "max_weight_per_asset": "Part maximale par actif dans le panier simulé (règle du profil)",
    "max_weight_per_sector": "Part maximale par secteur dans le panier simulé (règle du profil)",
    "max_weight_crypto": "Part maximale en cryptoactifs dans le panier simulé (règle du profil)",
}


# --- sortie brute du modèle -------------------------------------------------------------------
class ConstraintsDraft(BaseModel):
    max_weight_per_asset: Optional[float] = None
    max_weight_per_sector: Optional[float] = None
    max_weight_crypto: Optional[float] = None
    esg_exclusion: Optional[bool] = None
    speculatif: Optional[str] = None


class RationaleItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str                       # « weights.diversification », « hard_constraints.max_weight_per_sector »
    because: str
    evidence_ids: tuple[str, ...] = ()
    claim_kind: ClaimKind = "HYPOTHESE"


class WeightingDraft(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: ConstraintsDraft = Field(default_factory=ConstraintsDraft)
    preferred_themes: list[str] = Field(default_factory=list)
    avoided_themes: list[str] = Field(default_factory=list)
    rationale: list[RationaleItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


# --- sortie validée ---------------------------------------------------------------------------
class ProfileFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    kind: str  # objectif | tolerance | horizon | preference
    text: str


class WeightingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile: Profile
    profile_weights: ProfileWeights
    risk_level: str
    preferred_themes: tuple[str, ...] = ()
    avoided_themes: tuple[str, ...] = ()
    rationale: tuple[RationaleItem, ...] = ()
    deviations: tuple[str, ...] = ()            # écarts au gabarit, champ par champ
    missing_information: tuple[str, ...] = ()
    facts: tuple[ProfileFact, ...] = ()         # phrases du profil (preuves FAIT)
    constraint_evidence: dict[str, str] = {}    # règle -> preuve HYPOTHESE
    weight_evidence: dict[str, str] = {}        # critère -> preuve HYPOTHESE
    limit_evidence: dict[str, str] = {}         # volatilite / perte_max -> preuve HYPOTHESE

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return (
            *(fact.evidence_id for fact in self.facts),
            *self.constraint_evidence.values(),
            *self.weight_evidence.values(),
            *self.limit_evidence.values(),
        )

    def fact(self, kind: str) -> Optional[ProfileFact]:
        return next((fact for fact in self.facts if fact.kind == kind), None)

    def rationale_evidence(self, field: str) -> tuple[str, ...]:
        """Phrases du profil à l'origine d'une valeur (ex. le souhait de diversification)."""
        ids: list[str] = []
        for item in self.rationale:
            if item.field == field:
                ids.extend(item.evidence_ids)
        return tuple(dict.fromkeys(ids))


# --- gabarit ----------------------------------------------------------------------------------
def template_for(profile: Profile, personas: Mapping) -> ProfileWeights:
    """Gabarit de départ : le persona lui-même, sinon le persona du même niveau de risque."""
    entries = {p["id"]: p for p in personas["personas"]}
    key = profile.id if profile.id in entries else TEMPLATE_BY_LEVEL[tolerance_level(profile.tolerance_risque)]
    return ProfileWeights.from_persona(entries[key])


def _horizon_text(profile: Profile) -> str:
    low, high = profile.horizon_annees.min, profile.horizon_annees.max
    return f"{low} ans ou plus" if high is None else f"{low} à {high} ans"


# --- garde-fous du code -----------------------------------------------------------------------
def bound_weights(proposed: Mapping[str, float], template: Mapping[str, float]) -> dict[str, float]:
    """Poids bornés à ± MAX_WEIGHT_SHIFT autour du gabarit, dans [0, 1], puis renormalisés."""
    bounded: dict[str, float] = {}
    for criterion in CRITERIA:
        base = float(template[criterion])
        value = proposed.get(criterion, base)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = base
        if value != value:  # NaN
            value = base
        low, high = max(0.0, base - MAX_WEIGHT_SHIFT), min(1.0, base + MAX_WEIGHT_SHIFT)
        bounded[criterion] = min(high, max(low, value))
    total = sum(bounded.values())
    if total <= 0:
        return dict(template)
    normalized = {criterion: round(value / total, 6) for criterion, value in bounded.items()}
    # Corrige l'arrondi sur le plus grand poids pour que la somme vaille exactement 1.
    largest = max(normalized, key=normalized.get)
    normalized[largest] = round(normalized[largest] + (1.0 - sum(normalized.values())), 6)
    return normalized


def tighten_constraints(template: HardConstraints, draft: ConstraintsDraft) -> HardConstraints:
    """Le modèle peut seulement resserrer une contrainte dure, jamais l'assouplir."""
    def cap(name: str) -> float:
        base = getattr(template, name)
        proposed = getattr(draft, name)
        if proposed is None or not 0.0 <= proposed <= 1.0:
            return base
        if name == "max_weight_per_asset" and proposed <= 0.0:
            return base  # une part nulle par actif viderait le panier
        return min(base, float(proposed))

    speculatif = template.speculatif
    if draft.speculatif in _SPECULATIF_ORDER:
        speculatif = max(speculatif, draft.speculatif, key=_SPECULATIF_ORDER.index)
    return HardConstraints(
        max_weight_per_asset=cap("max_weight_per_asset"),
        max_weight_per_sector=cap("max_weight_per_sector"),
        max_weight_crypto=cap("max_weight_crypto"),
        esg_exclusion=template.esg_exclusion or bool(draft.esg_exclusion),
        speculatif=speculatif,
    )


def _clean_themes(themes: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(theme for theme in themes if theme in THEMES))


# --- agent ------------------------------------------------------------------------------------
def weigh_profile(
    profile: Profile,
    template: ProfileWeights,
    client: LLMClient,
    ledger: EvidenceLedger,
    registry: SourcesRegistry,
    *,
    forbidden: Iterable[str] = (),
    profile_source: str = SOURCE_PROFILE,
) -> tuple[WeightingResult, CallInfo]:
    """Exécute l'agent de pondération et applique les garde-fous."""
    as_of: date = ledger.as_of
    profile_src = registry.require_used(profile_source).as_evidence_source()
    hypothesis_src = registry.require_used(SOURCE_HYPOTHESES).as_evidence_source()

    def add(kind: ClaimKind, statement: str, *, source, value=None, unit=None, produced_by: str,
            processing: str, limits: str) -> str:
        return ledger.add(EvidenceDraft(
            type="profile", claim_kind=kind, subject=profile.id, statement=statement, value=value, unit=unit,
            observed_at=as_of, published_at=as_of, source=source, processing=processing,
            produced_by=f"agents.profile_weighting.{produced_by}@{VERSION}", limits=limits,
        )).evidence_id

    # 1. Phrases du profil : preuves FAIT, avant tout appel au modèle.
    fact_limits = "Profil fictif déclaré ; aucune donnée personnelle réelle."
    statements: list[tuple[str, str]] = []
    if profile.objectif:
        statements.append(("objectif", f"Objectif déclaré : {profile.objectif}"))
    statements.append(("tolerance", f"Tolérance au risque déclarée : {profile.tolerance_risque}"))
    statements.append(("horizon", f"Horizon de placement déclaré : {_horizon_text(profile)}"))
    statements.extend(("preference", f"Préférence déclarée : {text}") for text in profile.preferences)
    facts = tuple(
        ProfileFact(
            evidence_id=add("FAIT", text, source=profile_src, produced_by="profil",
                            processing="Recopie du profil déclaré, sans transformation", limits=fact_limits),
            kind=kind, text=text,
        )
        for kind, text in statements
    )
    fact_ids = {fact.evidence_id for fact in facts}

    # 2. Appel au modèle.
    prompt = load_prompt(STEP)
    level = tolerance_level(profile.tolerance_risque)
    payload = {
        "profile": profile.model_dump(mode="json"),
        "facts": [fact.model_dump() for fact in facts],
        "template": {
            "weights": dict(template.weights),
            "hard_constraints": template.constraints.model_dump(),
        },
        "criteria": dict(CRITERION_LABELS),
        "themes": {theme: spec["label"] for theme, spec in THEMES.items()},
        "max_weight_shift": MAX_WEIGHT_SHIFT,
    }
    draft, info = structured_call(client, step=STEP, prompt=prompt, payload=payload, schema=WeightingDraft,
                                  tier=TIER_STRONG)

    # 3. Garde-fous : bornes, normalisation, resserrement seulement, vocabulaire fermé.
    weights = bound_weights(draft.weights, template.weights)
    constraints = tighten_constraints(template.constraints, draft.constraints)
    avoided = _clean_themes(draft.avoided_themes)
    preferred = tuple(theme for theme in _clean_themes(draft.preferred_themes) if theme not in avoided)

    deviations: list[str] = []
    for criterion in CRITERIA:
        if abs(weights[criterion] - float(template.weights[criterion])) > 1e-6:
            deviations.append(f"weights.{criterion}")
    for name, value in constraints.model_dump().items():
        if value != getattr(template.constraints, name):
            deviations.append(f"hard_constraints.{name}")

    known_fields = {f"weights.{c}" for c in CRITERIA} | {f"hard_constraints.{n}" for n in HardConstraints.model_fields}
    forbidden = tuple(forbidden)
    rationale: list[RationaleItem] = []
    for item in draft.rationale:
        if item.field not in known_fields:
            continue
        ids = tuple(i for i in dict.fromkeys(item.evidence_ids) if i in fact_ids)
        check = check_claim(Claim(text=item.because, evidence_ids=ids), ledger, as_of, forbidden)
        if check.ok:  # justification sourcée, sans chiffre non étayé ni formulation refusée
            rationale.append(RationaleItem(field=item.field, because=check.claim.text, evidence_ids=ids))

    profile_weights = ProfileWeights(
        persona_id=profile.id, weights=weights, constraints=constraints, rationale=profile.objectif,
        missing_info=tuple(draft.missing_information),
    )

    # 4. Valeurs retenues : preuves HYPOTHESE (choix de l'équipe, à calibrer).
    hypothesis_limits = "Hypothèse de l'équipe, à calibrer ; ne décrit aucun fait de marché."
    constraint_evidence = {
        name: add("HYPOTHESE", label, source=hypothesis_src, value=getattr(constraints, name) * 100.0, unit="%",
                  produced_by="contraintes", processing="Gabarit du profil, resserré si le profil le demande",
                  limits=hypothesis_limits)
        for name, label in CONSTRAINT_LABELS.items()
    }
    weight_evidence = {
        criterion: add("HYPOTHESE", f"Poids du critère « {CRITERION_LABELS[criterion]} » dans le profil",
                       source=hypothesis_src, value=weights[criterion] * 100.0, unit="%", produced_by="poids",
                       processing=f"Gabarit du profil, ajusté d'au plus {MAX_WEIGHT_SHIFT * 100:.0f} points, renormalisé",
                       limits=hypothesis_limits)
        for criterion in CRITERIA
    }
    max_vol, max_loss = RISK_LIMITS[level]
    limit_evidence = {
        "volatilite": add("HYPOTHESE", f"Repère de volatilité annualisée pour une tolérance au risque {level}",
                          source=hypothesis_src, value=max_vol, unit="%", produced_by="reperes",
                          processing="Repère indicatif par niveau de tolérance au risque", limits=hypothesis_limits),
        "perte_max": add("HYPOTHESE", f"Repère de perte maximale pour une tolérance au risque {level}",
                         source=hypothesis_src, value=max_loss, unit="%", produced_by="reperes",
                         processing="Repère indicatif par niveau de tolérance au risque", limits=hypothesis_limits),
    }

    result = WeightingResult(
        profile=profile, profile_weights=profile_weights, risk_level=level,
        preferred_themes=preferred, avoided_themes=avoided, rationale=tuple(rationale),
        deviations=tuple(deviations), missing_information=tuple(draft.missing_information),
        facts=facts, constraint_evidence=constraint_evidence, weight_evidence=weight_evidence,
        limit_evidence=limit_evidence,
    )
    return result, info
