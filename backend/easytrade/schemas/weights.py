"""ProfileWeights : contraintes dures, poids par critère, justification, informations manquantes.

Conception : docs/03_DECISION_ENGINE.md
Règles :
- Les sept critères sont couverts exactement une fois.
- Chaque poids est dans [0, 1] et leur somme vaut 1 (± tolérance).
- Les bornes de parts (`max_weight_*`) sont dans [0, 1].
Source des valeurs de départ : data/reference/personas.json (hypothèses à calibrer).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

CRITERIA: tuple[str, ...] = (
    "croissance",
    "stabilite",
    "diversification",
    "esg",
    "qualite",
    "horizon",
    "preferences",
)

# Libellés affichés (textes, preuves). Les identifiants de `CRITERIA` restent sans accent.
CRITERION_LABELS: dict[str, str] = {
    "croissance": "croissance",
    "stabilite": "stabilité",
    "diversification": "diversification",
    "esg": "ESG",
    "qualite": "qualité",
    "horizon": "tenue sur l'horizon",
    "preferences": "préférences déclarées",
}

Speculatif = Literal["permis", "exclu", "signalé"]
WEIGHT_SUM_TOL = 1e-6


class HardConstraints(BaseModel):
    """Contraintes dures : elles écartent un actif, elles ne le classent pas."""

    model_config = ConfigDict(frozen=True)

    max_weight_per_asset: float
    max_weight_per_sector: float
    max_weight_crypto: float
    esg_exclusion: bool = False
    speculatif: Speculatif = "permis"

    @model_validator(mode="after")
    def _bounds(self) -> "HardConstraints":
        for name in ("max_weight_per_asset", "max_weight_per_sector", "max_weight_crypto"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} doit être dans [0, 1] ; reçu {value}")
        return self


class ProfileWeights(BaseModel):
    """Poids par critère et contraintes dures d'un persona."""

    model_config = ConfigDict(frozen=True)

    persona_id: str
    weights: dict[str, float]
    constraints: HardConstraints
    rationale: str = ""
    missing_info: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_weights(self) -> "ProfileWeights":
        keys = set(self.weights)
        if keys != set(CRITERIA):
            raise ValueError(
                f"Les poids doivent couvrir exactement {CRITERIA} ; reçu {sorted(keys)}"
            )
        for name, value in self.weights.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Poids {name}={value} hors de [0, 1]")
        total = sum(self.weights.values())
        if abs(total - 1.0) > WEIGHT_SUM_TOL:
            raise ValueError(f"La somme des poids doit valoir 1 (± {WEIGHT_SUM_TOL}) ; reçu {total}")
        return self

    @classmethod
    def from_persona(cls, persona: dict) -> "ProfileWeights":
        """Construit depuis une entrée de data/reference/personas.json."""
        constraints = persona["contraintes"]
        return cls(
            persona_id=persona["id"],
            weights=dict(persona["poids"]),
            constraints=HardConstraints(
                max_weight_per_asset=constraints["max_weight_per_asset"],
                max_weight_per_sector=constraints["max_weight_per_sector"],
                max_weight_crypto=constraints["max_weight_crypto"],
                esg_exclusion=constraints["esg_exclusion"],
                speculatif=constraints["speculatif"],
            ),
            rationale=persona.get("profil", {}).get("objectif", ""),
        )
