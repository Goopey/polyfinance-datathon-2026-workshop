"""GET /personas, GET /profiles/{id}, POST /profiles.

Conception : docs/01_ARCHITECTURE.md
Les profils sont fictifs : aucune donnée personnelle n'est demandée ni conservée.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from easytrade.api.deps import get_service
from easytrade.api.service import ApiService
from easytrade.schemas.api import ProfileDraft, ProfileWeightsView

router = APIRouter(tags=["profils"])



@router.get("/personas")
def list_personas(service: ApiService = Depends(get_service)) -> list[dict[str, Any]]:
    """Les trois personas de l'énoncé, avec leurs poids et contraintes de départ."""
    return service.personas()


@router.get("/profiles/{profile_id}", response_model=ProfileWeightsView)
def get_profile(profile_id: str, service: ApiService = Depends(get_service)) -> ProfileWeightsView:
    """Sortie de l'agent de pondération : règles, poids et justification d'un profil."""
    return service.profile_view(profile_id)


@router.post("/profiles", response_model=ProfileWeightsView)
def create_profile(draft: ProfileDraft, service: ApiService = Depends(get_service)) -> ProfileWeightsView:
    """Crée un profil fictif depuis le questionnaire, ou une variante à poids modifiés."""
    return service.create_profile(draft)
