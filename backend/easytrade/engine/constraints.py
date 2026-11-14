"""Contraintes dures du profil : admissibles / rejetés avec motif.

Conception : docs/03_DECISION_ENGINE.md (section « Contraintes dures »)
Une contrainte dure **écarte** un actif ; un poids le **classe**. La différence est montrée à
l'utilisateur : « écarté par une règle de votre profil » contre « moins bien classé ».

Admissibilité au niveau d'un actif (ce module) :
- crypto exclu quand la part maximale en crypto vaut 0 ;
- actifs « hautement spéculatifs » exclus quand `speculatif == "exclu"`, signalés quand « signalé » ;
- exclusion sur controverse ESG documentée quand `esg_exclusion` est vrai.
Les plafonds par actif et par secteur sont des garde-fous de *panier*, appliqués après le
classement (`basket_caps`), pas des critères d'admissibilité.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from easytrade.schemas.candidate import Asset, Rejection
from easytrade.schemas.weights import HardConstraints

# Classes d'actifs jugées « hautement spéculatives » dans le socle de départ (hypothèse assumée :
# la crypto ; à affiner avec des sources si l'on veut marquer certaines actions). Voir docs/03.
SPECULATIVE_CLASSES = frozenset({"crypto"})
CRYPTO_CLASS = "crypto"


@dataclass(frozen=True)
class ScreeningResult:
    eligible: tuple[Asset, ...]
    rejected: tuple[Rejection, ...]
    flags: dict[str, tuple[str, ...]]  # ticker -> drapeaux non bloquants (ex. « spéculatif signalé »)


def is_speculative(asset_class: str) -> bool:
    return asset_class in SPECULATIVE_CLASSES


def screen_assets(
    assets: pd.DataFrame,
    constraints: HardConstraints,
    esg_controversial: frozenset[str] = frozenset(),
) -> ScreeningResult:
    """Sépare l'univers en actifs admissibles et actifs écartés (avec motif)."""
    eligible: list[Asset] = []
    rejected: list[Rejection] = []
    flags: dict[str, tuple[str, ...]] = {}

    for _, row in assets.iterrows():
        asset = Asset.from_row(row)
        asset_flags: list[str] = []

        if asset.asset_class == CRYPTO_CLASS and constraints.max_weight_crypto == 0.0:
            rejected.append(Rejection(
                ticker=asset.ticker, name=asset.name, rule="max_weight_crypto",
                reason="Cryptoactif écarté : votre profil n'autorise aucune part en crypto.",
            ))
            continue

        if is_speculative(asset.asset_class):
            if constraints.speculatif == "exclu":
                rejected.append(Rejection(
                    ticker=asset.ticker, name=asset.name, rule="speculatif",
                    reason="Actif hautement spéculatif écarté par une règle de votre profil.",
                ))
                continue
            if constraints.speculatif == "signalé":
                asset_flags.append("spéculatif signalé")

        if constraints.esg_exclusion and asset.ticker in esg_controversial:
            rejected.append(Rejection(
                ticker=asset.ticker, name=asset.name, rule="esg_exclusion",
                reason="Écarté : controverse ESG documentée, exclue par votre profil.",
            ))
            continue

        eligible.append(asset)
        if asset_flags:
            flags[asset.ticker] = tuple(asset_flags)

    return ScreeningResult(eligible=tuple(eligible), rejected=tuple(rejected), flags=flags)


def basket_caps(constraints: HardConstraints) -> dict[str, float]:
    """Plafonds de panier (part max par actif / secteur / crypto), appliqués après le classement.

    Exposé pour l'étape de construction de panier simulé et les garde-fous de l'UI ; le moteur de
    classement ne s'en sert pas pour écarter un actif.
    """
    return {
        "max_weight_per_asset": constraints.max_weight_per_asset,
        "max_weight_per_sector": constraints.max_weight_per_sector,
        "max_weight_crypto": constraints.max_weight_crypto,
    }
