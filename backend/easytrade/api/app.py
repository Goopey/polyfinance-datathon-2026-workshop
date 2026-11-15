"""Application FastAPI et adaptateur Lambda.

Conception : docs/01_ARCHITECTURE.md (API)
Lancement local, depuis `backend/` :

    uvicorn easytrade.api.app:app --reload --port 8000

Le service (données, pipeline, runs en mémoire) est créé à la première requête : importer ce
module ne charge aucune donnée. `create_app(service)` permet aux tests d'injecter un service.

Aucune route ne passe d'ordre ni ne touche un compte : l'API lit des données publiques datées
et lance des analyses simulées (scénario S8, point 3).
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from easytrade.api import routes_assets, routes_profiles, routes_runs
from easytrade.api.deps import get_service  # noqa: F401  (réexporté)
from easytrade.api.service import ApiService, InvalidRequest, NotFound

def create_app(service: Optional[ApiService] = None) -> FastAPI:
    app = FastAPI(
        title="EasyTrade — API",
        description="Simulateur d'aide à la décision. Aucune transaction réelle ; ceci n'est pas un conseil financier.",
        version="0.1.0",
    )
    app.state.service = service
    # L'application mobile (Expo web ou appareil) appelle l'API depuis une autre origine.
    origins = [o.strip() for o in os.environ.get("EASYTRADE_CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, error: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InvalidRequest)
    async def _invalid(_: Request, error: InvalidRequest) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.get("/health", tags=["service"])
    def health() -> dict:
        return {"status": "ok", "simulation": True}

    app.include_router(routes_profiles.router)
    app.include_router(routes_runs.router)
    app.include_router(routes_assets.router)
    return app


app = create_app()

try:  # adaptateur AWS Lambda (P4) ; absent en local si mangum n'est pas installé
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:  # pragma: no cover
    handler = None
