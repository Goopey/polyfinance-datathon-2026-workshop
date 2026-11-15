"""POST /runs, GET /runs/{id}, GET /runs/{id}/trace.

Conception : docs/01_ARCHITECTURE.md
Une analyse est asynchrone : `POST /runs` rend un identifiant, le mobile interroge `GET /runs/{id}`
et affiche les étapes au fur et à mesure.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from easytrade.api.deps import get_service
from easytrade.api.service import ApiService
from easytrade.schemas.api import RunCreated, RunRequest, RunStatusView
from easytrade.schemas.trace import RunTrace

router = APIRouter(tags=["analyses"])



@router.post("/runs", response_model=RunCreated)
def start_run(body: RunRequest, service: ApiService = Depends(get_service)) -> RunCreated:
    """Lance une analyse simulée. Avec `requested_ticker` : « Tester une idée »."""
    return RunCreated(run_id=service.start_run(body))


@router.get("/runs/{run_id}", response_model=RunStatusView)
def get_run(run_id: str, service: ApiService = Depends(get_service)) -> RunStatusView:
    return service.run_status(run_id)


@router.get("/runs/{run_id}/trace", response_model=RunTrace)
def get_trace(run_id: str, service: ApiService = Depends(get_service)) -> RunTrace:
    """Étapes réellement exécutées : entrées, outils, sorties, modèle, statut, contrôles."""
    return service.trace(run_id)
