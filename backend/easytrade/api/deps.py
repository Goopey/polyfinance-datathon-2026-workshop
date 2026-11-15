"""Dépendance commune des routes : le service partagé de l'application.

Le service (données, pipeline, runs en mémoire) est créé à la première requête : importer
l'application ne charge aucune donnée.
"""
from __future__ import annotations

import os
import threading

from fastapi import Request

from easytrade.api.service import ApiService

_lock = threading.Lock()


def make_service() -> ApiService:
    """En local : runs en mémoire, exécutés dans des fils. Sur AWS (`EASYTRADE_ENV=aws`) : DynamoDB,
    Step Functions et S3 (`api/aws_service.py`)."""
    if os.environ.get("EASYTRADE_ENV") == "aws":
        from easytrade.api.aws_service import AwsApiService

        return AwsApiService()
    return ApiService()


def get_service(request: Request) -> ApiService:
    state = request.app.state
    if getattr(state, "service", None) is None:
        with _lock:
            if getattr(state, "service", None) is None:
                state.service = make_service()
    return state.service
