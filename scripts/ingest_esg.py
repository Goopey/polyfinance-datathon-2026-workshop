"""Transforme les fichiers d'émissions de GES de data/raw/external/ en lignes de data/reference/esg_evidence.csv.

Usage (depuis la racine du dépôt, avec le venv du backend) :
    python scripts/ingest_esg.py                  # écrit le fichier
    python scripts/ingest_esg.py --dry-run        # affiche l'audit sans rien écrire
    python scripts/ingest_esg.py --retrieved-at 2026-11-15

Fichiers attendus dans data/raw/external/ (jamais versionnés) : voir CONTRIBUTING.md, « Données ESG ».
Conception : docs/04_DONNEES.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from easytrade.config import load_settings  # noqa: E402
from easytrade.data.external_esg import ExternalFileError  # noqa: E402
from easytrade.data.point_in_time import PointInTimeStore  # noqa: E402
from easytrade.data.sources_registry import SourcesRegistry  # noqa: E402
from easytrade.ingestion.esg import build_esg_rows, check_sources, merge_reference_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--external-dir", type=Path, help="dossier des fichiers bruts (défaut : data/raw/external)")
    parser.add_argument("--retrieved-at", type=date.fromisoformat, help="date d'extraction AAAA-MM-JJ (défaut : horodatage du fichier canadien)")
    parser.add_argument("--dry-run", action="store_true", help="n'écrit rien, affiche l'audit")
    args = parser.parse_args()

    settings = load_settings()
    external = args.external_dir or settings.data_dir / "raw" / "external"
    target = settings.reference_dir / "esg_evidence.csv"
    try:
        universe = set(PointInTimeStore.from_settings(settings).assets()["ticker"])
        result = build_esg_rows(external, args.retrieved_at, universe)
    except ExternalFileError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    problems = check_sources(SourcesRegistry.load(settings.reference_dir), result.rows)
    print(json.dumps(result.audit, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if problems:
        print("\nSources à régulariser avant d'utiliser ces lignes (règle 3 de CONTRIBUTING.md) :", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"\n{len(result.rows)} ligne(s) calculée(s), rien d'écrit (--dry-run).")
        return 0
    kept, written = merge_reference_file(target, result.rows)
    print(f"\n{target.relative_to(REPO_ROOT)} : {written} ligne(s) du script, {kept} ligne(s) manuelle(s) conservée(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
