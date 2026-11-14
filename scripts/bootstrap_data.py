"""Vérifie la présence du jeu de départ et lance l'ingestion vers data/curated.

Usage : python scripts/bootstrap_data.py   (depuis la racine du dépôt, avec le venv du backend)
Conception : docs/04_DONNEES.md
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from easytrade.config import load_settings  # noqa: E402
from easytrade.ingestion.starter_kit import build_curated  # noqa: E402

REQUIRED = [
    "assets_universe.csv", "prices_daily.csv", "corporate_actions.csv",
    "fx_usdcad_daily.csv", "macro_rates.csv", "sources_metadata.csv",
]


def main() -> int:
    settings = load_settings()
    missing = [name for name in REQUIRED if not (settings.starter_dir / name).exists()]
    if missing:
        print(f"Jeu de départ incomplet dans {settings.starter_dir} : {', '.join(missing)}", file=sys.stderr)
        print("Régénérer avec data/raw/starter/build_dataset.py ou recopier les fichiers.", file=sys.stderr)
        return 1
    outputs = build_curated(settings)
    for name, path in outputs.paths.items():
        print(f"{name:15s} {path.relative_to(REPO_ROOT)}")
    print(f"preuves : {outputs.evidence_count} ; contrôles qualité : {outputs.quality_summary}")
    return 1 if outputs.quality_summary.get("fail", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
