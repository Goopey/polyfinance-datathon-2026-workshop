"""Points de contrôle visibles, inscrits dans la trace, et garde-fous de panier.

Conception : docs/08_CONFORMITE.md (fonction de gouvernance), docs/03_DECISION_ENGINE.md
Trois points de contrôle, chacun rendu sous forme de `ControlResult` que le pipeline inscrit
dans la trace (`kind = controle`) :
1. avant le débat : contraintes dures appliquées, candidats sans preuve écartés ;
2. à la décision : plafonds du panier simulé, diversité minimale, « aucune recommandation » ;
3. avant l'affichage : vérificateur de fidélité, filtre de formulations.

Garde-fous de panier (hypothèse de l'équipe) : les pistes retenues forment un panier simulé à
parts égales. Sa taille est le plus petit nombre de pistes qui respecte la part maximale par
actif (15 % → 7 pistes, 10 % → 10 pistes). On parcourt le classement dans l'ordre ; une piste
qui ferait dépasser le plafond par secteur ou la part maximale en crypto est **déclassée**, avec
le motif, et la suivante est examinée. Python déterministe, aucun LLM.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from easytrade.engine.constraints import CRYPTO_CLASS
from easytrade.schemas.candidate import Rejection, ScoredCandidate
from easytrade.schemas.weights import HardConstraints

RULE_SECTOR = "panier_max_weight_per_sector"
RULE_CRYPTO = "panier_max_weight_crypto"
# Groupes de concentration (hypothèse de l'équipe) : des secteurs de l'univers qui portent le même
# risque sont comptés ensemble pour le plafond par secteur. Sans cela, trois pistes technologiques
# classées sous trois libellés différents passeraient chacune sous le plafond. À remplacer par la
# corrélation au panier quand elle alimentera le critère de diversification (bloc G).
CONCENTRATION_GROUPS: dict[str, frozenset[str]] = {
    "Technologies": frozenset({
        "Information Technology", "Communication Services", "Broad market (U.S. growth/tech-heavy)",
    }),
    "Actions américaines, marché large": frozenset({
        "Broad market (U.S.)", "Broad market (U.S., ESG-screened)",
    }),
    "Obligations": frozenset({
        "Bonds (Canada aggregate)", "Bonds (Canada ultra short-term)", "Bonds (U.S. aggregate)",
        "Bonds (U.S. long Treasury)",
    }),
}
TECHNOLOGY_GROUP = "Technologies"
MAX_BASKET_SIZE = 20
MIN_DISTINCT_GROUPS = 3  # docs/03 : au moins trois secteurs ou classes d'actifs distincts
_EPS = 1e-9


@dataclass(frozen=True)
class ControlResult:
    name: str
    passed: bool
    note: str


@dataclass(frozen=True)
class BasketSelection:
    retained: tuple[ScoredCandidate, ...]
    displaced: tuple[Rejection, ...]
    size: int              # taille visée du panier simulé
    max_per_sector: int    # nombre maximal de pistes d'un même secteur
    max_crypto: int        # nombre maximal de pistes en crypto

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(candidate.ticker for candidate in self.retained)


def concentration_group(sector: str) -> str:
    """Groupe compté pour le plafond par secteur : un groupe de secteurs liés, sinon le secteur."""
    for group, sectors in CONCENTRATION_GROUPS.items():
        if sector in sectors:
            return group
    return sector


def basket_size(constraints: HardConstraints) -> int:
    """Plus petit nombre de pistes à parts égales qui respecte la part maximale par actif."""
    if constraints.max_weight_per_asset <= 0:
        return MAX_BASKET_SIZE
    return max(1, min(MAX_BASKET_SIZE, math.ceil(1.0 / constraints.max_weight_per_asset - _EPS)))


def select_basket(ranking: Sequence[ScoredCandidate], constraints: HardConstraints) -> BasketSelection:
    """Pistes retenues dans l'ordre du classement, sous les plafonds du profil."""
    size = basket_size(constraints)
    per_sector = max(1, math.floor(constraints.max_weight_per_sector * size + _EPS))
    crypto_max = math.floor(constraints.max_weight_crypto * size + _EPS)

    retained: list[ScoredCandidate] = []
    displaced: list[Rejection] = []
    sector_count: dict[str, int] = {}
    crypto_count = 0
    for candidate in ranking:
        if len(retained) >= size:
            break
        if candidate.asset_class == CRYPTO_CLASS and crypto_count >= crypto_max:
            displaced.append(Rejection(
                ticker=candidate.ticker, name=candidate.name, rule=RULE_CRYPTO,
                reason=(
                    "Déclassé pour cause de concentration : la part maximale en crypto de "
                    f"{constraints.max_weight_crypto * 100:.0f} % est déjà atteinte dans le panier simulé."
                ),
            ))
            continue
        group = concentration_group(candidate.sector)
        if sector_count.get(group, 0) >= per_sector:
            displaced.append(Rejection(
                ticker=candidate.ticker, name=candidate.name, rule=RULE_SECTOR,
                reason=(
                    "Déclassé pour cause de concentration : le plafond de "
                    f"{constraints.max_weight_per_sector * 100:.0f} % par secteur est déjà atteint "
                    f"pour « {group} » dans le panier simulé."
                ),
            ))
            continue
        retained.append(candidate)
        sector_count[group] = sector_count.get(group, 0) + 1
        crypto_count += candidate.asset_class == CRYPTO_CLASS
    return BasketSelection(tuple(retained), tuple(displaced), size, per_sector, crypto_max)


def basket_shares(retained: Sequence[ScoredCandidate]) -> dict:
    """Parts du panier simulé à parts égales : par actif, par secteur, en crypto."""
    n = len(retained)
    if n == 0:
        return {"per_asset": 0.0, "per_sector": {}, "crypto": 0.0}
    sectors: dict[str, float] = {}
    for candidate in retained:
        group = concentration_group(candidate.sector)
        sectors[group] = sectors.get(group, 0.0) + 1.0 / n
    crypto = sum(1 for candidate in retained if candidate.asset_class == CRYPTO_CLASS) / n
    return {"per_asset": 1.0 / n, "per_sector": sectors, "crypto": crypto}


# --- points de contrôle -----------------------------------------------------------------------
def control_pre_debate(*, universe: int, rejected_by_rule: int, without_evidence: int,
                       candidates: int) -> ControlResult:
    """Contrôle 1 : contraintes dures appliquées, candidats sans preuve écartés."""
    return ControlResult(
        "controle.avant_debat", True,
        f"{universe} actifs examinés ; {rejected_by_rule} écartés par une règle du profil ; "
        f"{without_evidence} écartés faute d'indicateurs valides ; {candidates} candidats classés.",
    )


def control_basket(selection: BasketSelection, constraints: HardConstraints) -> ControlResult:
    """Contrôle 2a : plafonds du panier simulé tenus (par actif, par secteur, crypto)."""
    shares = basket_shares(selection.retained)
    problems: list[str] = []
    if selection.retained:
        if shares["per_asset"] > constraints.max_weight_per_asset + _EPS:
            problems.append(
                f"panier incomplet ({len(selection.retained)} pistes pour {selection.size} visées) : "
                "la part par actif dépasse le plafond"
            )
        worst_sector = max(shares["per_sector"].values())
        if worst_sector > constraints.max_weight_per_sector + _EPS:
            problems.append("plafond par secteur dépassé")
        if shares["crypto"] > constraints.max_weight_crypto + _EPS:
            problems.append("part maximale en crypto dépassée")
    note = (
        f"{len(selection.retained)} pistes retenues, {len(selection.displaced)} déclassées pour concentration ; "
        f"au plus {selection.max_per_sector} par secteur et {selection.max_crypto} en crypto."
    )
    if problems:
        note += " Écarts : " + " ; ".join(problems) + "."
    return ControlResult("controle.plafonds_panier", not problems, note)


def control_diversification(selection: BasketSelection, minimum: int = MIN_DISTINCT_GROUPS) -> ControlResult:
    """Contrôle 2b : au moins `minimum` groupes de secteurs distincts parmi les pistes retenues."""
    groups = sorted({concentration_group(candidate.sector) for candidate in selection.retained})
    passed = len(groups) >= minimum or not selection.retained
    return ControlResult(
        "controle.diversification", passed,
        f"{len(groups)} groupes de secteurs distincts parmi les pistes retenues (minimum {minimum}).",
    )


def control_no_recommendation(no_recommendation: bool, reason: str) -> ControlResult:
    """Contrôle 2c : « aucune recommandation » est une sortie valide, jamais une piste forcée."""
    prefix = "Aucune recommandation : "
    # La raison du moteur porte parfois déjà le préfixe (engine/decision.py) : ne pas le doubler.
    note = (reason if reason.startswith(prefix) else f"{prefix}{reason}") if no_recommendation else "Des pistes sont présentées."
    return ControlResult("controle.aucune_recommandation", True, note)


def control_display(*, checked: int, first_pass_ok: int, first_pass_checked: int, removed: int,
                    remaining_issues: int, wording_hits: Optional[Iterable[str]] = None) -> ControlResult:
    """Contrôle 3 : vérificateur de fidélité et filtre de formulations, avant l'affichage."""
    hits = list(wording_hits or [])
    note = (
        f"{first_pass_ok}/{first_pass_checked} affirmations rédigées fidèles au premier passage ; "
        f"{removed} retirées ; {checked} affirmations de la sortie recontrôlées, "
        f"{remaining_issues} écart restant ; {len(hits)} formulation refusée."
    )
    return ControlResult("controle.avant_affichage", remaining_issues == 0 and not hits, note)
