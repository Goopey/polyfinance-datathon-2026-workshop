"""Profile : objectif, tolérance au risque, horizon, préférences (profil fictif).

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md
Bloc descriptif du persona. La pondération et les contraintes vivent dans `ProfileWeights`.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class HorizonYears(BaseModel):
    model_config = ConfigDict(frozen=True)

    min: int
    max: Optional[int] = None


class Profile(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    nom: str
    tolerance_risque: str
    horizon_annees: HorizonYears
    objectif: str = ""
    experience: str = ""
    preferences: tuple[str, ...] = ()

    @classmethod
    def from_persona(cls, persona: dict) -> "Profile":
        """Construit depuis une entrée de data/reference/personas.json."""
        profil = persona["profil"]
        horizon = profil["horizon_annees"]
        return cls(
            id=persona["id"],
            nom=profil["nom"],
            tolerance_risque=profil["tolerance_risque"],
            horizon_annees=HorizonYears(min=horizon["min"], max=horizon.get("max")),
            objectif=profil.get("objectif", ""),
            experience=profil.get("experience", ""),
            preferences=tuple(profil.get("preferences", ())),
        )
