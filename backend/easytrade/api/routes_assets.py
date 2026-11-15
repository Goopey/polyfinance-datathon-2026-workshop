"""GET /assets, GET /assets/{ticker}, GET /assets/{ticker}/graph, GET /evidence/{id}, GET /data.

Conception : docs/01_ARCHITECTURE.md
`run_id` : les identifiants de preuves sont propres à une analyse. Le mobile le transmet pour que
la fiche, le graphe et la preuve affichés soient ceux du run consulté ; sans `run_id`, la réponse
vient du registre « hors analyse » calculé à la date de référence.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from easytrade.api.deps import get_service
from easytrade.api.service import ApiService
from easytrade.schemas.api import AssetSheet, AssetSummary, DataOverview, DependencyGraph
from easytrade.schemas.evidence import Evidence

router = APIRouter(tags=["actifs et preuves"])



@router.get("/assets", response_model=list[AssetSummary])
def list_assets(service: ApiService = Depends(get_service)) -> list[AssetSummary]:
    """Univers d'actifs analysé (liste de « Tester une idée »)."""
    return service.assets()


@router.get("/assets/{ticker}", response_model=AssetSheet)
def get_asset(ticker: str, profile_id: Optional[str] = None, run_id: Optional[str] = None,
              service: ApiService = Depends(get_service)) -> AssetSheet:
    """Fiche : indicateurs situés dans l'univers et comparés aux repères du profil, signaux datés."""
    return service.asset_sheet(ticker, profile_id=profile_id, run_id=run_id)


@router.get("/assets/{ticker}/graph", response_model=DependencyGraph)
def get_graph(ticker: str, run_id: Optional[str] = None, service: ApiService = Depends(get_service)) -> DependencyGraph:
    """Graphe de dépendances sourcé, profondeur 1."""
    return service.graph(ticker, run_id=run_id)


@router.get("/evidence/{evidence_id}", response_model=Evidence)
def get_evidence(evidence_id: str, run_id: Optional[str] = None, service: ApiService = Depends(get_service)) -> Evidence:
    """Une preuve : source, dates d'observation, de publication et d'extraction, traitement, limites."""
    return service.evidence(evidence_id, run_id=run_id)


@router.get("/data", response_model=DataOverview)
def get_data(run_id: Optional[str] = None, service: ApiService = Depends(get_service)) -> DataOverview:
    """Sources utilisées et résultat des contrôles qualité (écran « Données »)."""
    return service.data_overview(run_id=run_id)
