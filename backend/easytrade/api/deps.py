"""Dépendance commune des routes : le service partagé de l'application.

Le service (données, pipeline, runs en mémoire) est créé à la première requête : importer
l'application ne charge aucune donnée.
"""
from __future__ import annotations

import threading

from fastapi import Request

from easytrade.api.service import ApiService

_lock = threading.Lock()


def get_service(request: Request) -> ApiService:
    state = request.app.state
    if getattr(state, "service", None) is None:
        with _lock:
            if getattr(state, "service", None) is None:
                state.service = ApiService()
    return state.service
