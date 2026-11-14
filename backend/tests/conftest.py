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
