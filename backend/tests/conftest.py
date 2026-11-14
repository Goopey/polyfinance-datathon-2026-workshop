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
