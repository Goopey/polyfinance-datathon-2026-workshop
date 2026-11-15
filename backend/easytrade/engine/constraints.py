"""Contraintes dures du profil : admissibles / rejetés avec motif.

Conception : docs/03_DECISION_ENGINE.md (section « Contraintes dures »)
Une contrainte dure **écarte** un actif ; un poids le **classe**. La différence est montrée à
l'utilisateur : « écarté par une règle de votre profil » contre « moins bien classé ».

Admissibilité au niveau d'un actif (ce module) :
- crypto exclu quand la part maximale en crypto vaut 0 ;
- actifs « hautement spéculatifs » exclus quand `speculatif == "exclu"`, signalés quand « signalé » ;
- exclusion sur controverse ESG documentée, ou sur émissions directes documentées au-dessus du seuil
  d'émetteur majeur (`engine.esg`), quand `esg_exclusion` est vrai.
Les plafonds par actif et par secteur sont des garde-fous de *panier*, appliqués après le
classement (`basket_caps`), pas des critères d'admissibilité.

Tolérance au risque (ajout du 2026-11-15, audit C2) : la tolérance déclarée est une **règle**, pas
seulement un poids. Un actif est écarté quand sa volatilité ou sa perte maximale observées dépassent
le repère du profil de plus de `SEVERE_RATIO` fois (tous les profils), ou, pour un profil prudent ou
modéré, quand il dépasse **les deux** repères à la fois. Un profil à tolérance élevée accepte ce
dépassement modéré avec réserve, de même qu'une classe que le profil autorise dans une poche plafonnée
(crypto avec `max_weight_crypto > 0`) : c'est alors le plafond qui encadre le risque. Tout dépassement
non éliminatoire laisse l'actif admissible avec le drapeau `RISK_FLAG` : son adéquation est plafonnée à « partielle »
(`engine.scoring.fit_level`). La même règle sert à « Tester une idée » (`engine.coherence`) : le
classement et le test d'une idée ne peuvent pas se contredire.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import pandas as pd

from easytrade.engine.esg import EMISSIONS_FOCUS_REASON, EMISSIONS_REASON, RULE_EMISSIONS
from easytrade.schemas.candidate import Asset, Rejection
from easytrade.schemas.weights import HardConstraints

# Classes d'actifs jugées « hautement spéculatives » dans le socle de départ (hypothèse assumée :
# la crypto ; à affiner avec des sources si l'on veut marquer certaines actions). Voir docs/03.
SPECULATIVE_CLASSES = frozenset({"crypto"})
CRYPTO_CLASS = "crypto"

# --- repères de risque par niveau de tolérance ---------------------------------------------------
# (volatilité annualisée maximale en %, perte maximale tolérée en %). Hypothèses de l'équipe
# (docs/03_DECISION_ENGINE.md), affichées comme telles.
RISK_LIMITS: dict[str, tuple[float, float]] = {
    "faible": (18.0, -20.0),
    "faible à modérée": (22.0, -25.0),  # entre les deux niveaux voisins (persona Robert)
    "modérée": (25.0, -30.0),
    "élevée": (45.0, -50.0),
}
SEVERE_RATIO = 1.5  # dépassement d'un repère au-delà duquel l'écart est jugé sévère
AGGRESSIVE_LEVEL = "élevée"
RULE_TOLERANCE = "tolerance_risque"
RISK_FLAG = "repère de risque dépassé"


def pct_fr(value: float) -> str:
    """Valeur d'un actif comparée à un repère : une décimale, virgule française (« 18,4 »). À l'entier
    près, 18,4 % s'écrirait « 18 % pour un repère de 18 % » et le dépassement deviendrait invisible."""
    return f"{value:.1f}".replace(".", ",")


def tolerance_level(tolerance_risque: str) -> str:
    """Niveau de tolérance normalisé, clé de `RISK_LIMITS`. Un libellé inconnu est lu « modérée »."""
    text = tolerance_risque.casefold()
    if "faible" in text and "mod" in text:
        return "faible à modérée"
    if "faible" in text:
        return "faible"
    if "mod" in text:
        return "modérée"
    if "lev" in text:  # élevé, élevée, eleve
        return "élevée"
    return "modérée"


@dataclass(frozen=True)
class RiskBreach:
    """Écart d'un actif aux repères de risque du profil."""

    over_volatility: bool
    over_drawdown: bool
    severe_volatility: bool
    severe_drawdown: bool
    capped_class: bool  # classe autorisée dans une poche plafonnée (le plafond encadre le risque)

    @property
    def any(self) -> bool:
        return self.over_volatility or self.over_drawdown

    @property
    def both(self) -> bool:
        return self.over_volatility and self.over_drawdown

    aggressive: bool = False  # tolérance élevée : un dépassement modéré des deux repères est accepté avec réserve

    @property
    def excluded(self) -> bool:
        """Écarté par la tolérance : dépassement sévère pour tous ; dépassement des deux repères pour un
        profil prudent ou modéré (hors poche plafonnée). Un profil à tolérance élevée garde l'actif avec
        réserve tant qu'il reste sous `SEVERE_RATIO` fois ses repères (« risque élevé » ≠ « tout passe »)."""
        if self.severe_volatility or self.severe_drawdown:
            return True
        return self.both and not self.capped_class and not self.aggressive


def risk_breach(
    level: str, volatility: Optional[float], max_drawdown: Optional[float], *, capped_class: bool = False,
) -> RiskBreach:
    """Compare la volatilité (%) et la perte maximale (%, négative) aux repères du niveau `level`.
    Une valeur absente ne crée aucun écart (elle est traitée comme « information manquante » ailleurs)."""
    max_vol, max_loss = RISK_LIMITS[level]
    over_vol = volatility is not None and volatility > max_vol
    over_dd = max_drawdown is not None and max_drawdown < max_loss
    return RiskBreach(
        over_volatility=over_vol,
        over_drawdown=over_dd,
        severe_volatility=over_vol and volatility > max_vol * SEVERE_RATIO,
        severe_drawdown=over_dd and max_drawdown < max_loss * SEVERE_RATIO,
        capped_class=capped_class,
        aggressive=level == AGGRESSIVE_LEVEL,
    )


def is_capped_class(asset_class: str, constraints: HardConstraints) -> bool:
    """Classe autorisée par le profil dans une poche plafonnée (aujourd'hui : la crypto)."""
    return asset_class == CRYPTO_CLASS and 0.0 < constraints.max_weight_crypto < 1.0


def tolerance_reason(level: str, volatility: Optional[float], max_drawdown: Optional[float]) -> str:
    """Motif lisible d'une exclusion par la tolérance ; chaque nombre vient d'une preuve citée
    (indicateurs de l'actif et repères du profil, voir `orchestration.pipeline`)."""
    max_vol, max_loss = RISK_LIMITS[level]
    parts = []
    if volatility is not None and volatility > max_vol:
        parts.append(f"volatilité annualisée de {pct_fr(volatility)} % pour un repère de {max_vol:.0f} %")
    if max_drawdown is not None and max_drawdown < max_loss:
        parts.append(f"perte maximale observée de {pct_fr(abs(max_drawdown))} % pour un repère de {abs(max_loss):.0f} %")
    return (f"Écarté : risque au-delà de votre tolérance au risque {level} ("
            + " ; ".join(parts) + ").")


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
    *,
    esg_emitters: frozenset[str] = frozenset(),
    esg_focus: bool = False,
    risk: Optional[Mapping[str, tuple[Optional[float], Optional[float]]]] = None,
    risk_level: Optional[str] = None,
) -> ScreeningResult:
    """Sépare l'univers en actifs admissibles et actifs écartés (avec motif).

    `esg_controversial` / `esg_emitters` : titres avec une controverse documentée / émetteurs majeurs
    documentés (`engine.esg`), écartés quand le profil a `esg_exclusion` ; les émetteurs majeurs le sont aussi
    quand `esg_focus` (poids ESG d'au moins `engine.esg.ESG_FOCUS_WEIGHT`, « grande importance »).
    `risk` (ticker → (volatilité %, perte maximale %)) et `risk_level` activent la règle de tolérance
    au risque. Sans eux, seules les contraintes du profil s'appliquent (tests unitaires historiques).
    """
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

        if (constraints.esg_exclusion or esg_focus) and asset.ticker in esg_emitters:
            rejected.append(Rejection(
                ticker=asset.ticker, name=asset.name, rule=RULE_EMISSIONS,
                reason=EMISSIONS_REASON if constraints.esg_exclusion else EMISSIONS_FOCUS_REASON,
            ))
            continue

        if risk is not None and risk_level is not None and asset.ticker in risk:
            volatility, drawdown = risk[asset.ticker]
            breach = risk_breach(risk_level, volatility, drawdown,
                                 capped_class=is_capped_class(asset.asset_class, constraints))
            if breach.excluded:
                rejected.append(Rejection(
                    ticker=asset.ticker, name=asset.name, rule=RULE_TOLERANCE,
                    reason=tolerance_reason(risk_level, volatility, drawdown),
                ))
                continue
            if breach.any:
                asset_flags.append(RISK_FLAG)

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
