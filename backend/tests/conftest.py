"""Fixtures communes : chemins des données et personas."""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def data_dir():
    return REPO_ROOT / "data"


@pytest.fixture(scope="session")
def personas(data_dir):
    with open(data_dir / "reference" / "personas.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def settings(data_dir):
    from easytrade.config import Settings

    if not (data_dir / "raw" / "starter" / "prices_daily.csv").exists():
        pytest.skip("Jeu de départ absent de data/raw/starter/")
    return Settings(data_dir=data_dir)


@pytest.fixture(scope="session")
def store(settings):
    from easytrade.data.point_in_time import PointInTimeStore

    return PointInTimeStore.from_settings(settings)


@pytest.fixture(scope="session")
def registry(settings):
    from easytrade.data.sources_registry import SourcesRegistry

    return SourcesRegistry.load(settings.reference_dir)


@pytest.fixture(scope="session")
def forbidden(data_dir):
    from easytrade.explain.wording import load_forbidden

    return load_forbidden(data_dir / "reference")


@pytest.fixture(scope="session")
def workspace(settings, store, registry, personas, forbidden):
    """Ressources partagées du pipeline (données chargées une seule fois par session)."""
    from easytrade.orchestration.pipeline import Workspace

    return Workspace(settings=settings, store=store, registry=registry, personas=personas, forbidden=forbidden)


@pytest.fixture(scope="session")
def pipeline_run(workspace):
    """Exécute le pipeline avec les agents simulés (aucun modèle) ; résultats mis en cache par session."""
    from easytrade.agents.simulated import simulated_client
    from easytrade.orchestration.pipeline import run_pipeline

    cache = {}

    def run(persona, ticker=None, as_of=None):
        key = (persona, ticker, as_of)
        if key not in cache:
            cache[key] = run_pipeline(persona, requested_ticker=ticker, as_of=as_of, client=simulated_client(),
                                      workspace=workspace)
        return cache[key]

    return run
