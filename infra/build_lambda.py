"""Prépare le code des fonctions Lambda, sans Docker.

Conception : docs/06_AWS.md, infra/README.md
À lancer avant `cdk synth` / `cdk deploy`, depuis `infra/` :

    python build_lambda.py

Produit :
- `build/app/easytrade/`   le paquet du backend (prompts compris), sans les tests ;
- `build/layer/python/`    les dépendances (pandas, numpy, pydantic, fastapi, mangum), téléchargées en
                           roues Linux x86_64 pour Python 3.12 (`pip --platform`), donc construites sur
                           Windows ou macOS sans Docker. boto3 est fourni par l'environnement Lambda.
Les données ne sont pas dans le paquet : elles sont copiées sur S3 au déploiement et lues au démarrage.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parent
REPO = INFRA.parent
BUILD = INFRA / "build"
APP = BUILD / "app"
LAYER = BUILD / "layer" / "python"
PYTHON_VERSION = "3.12"
PLATFORM = "manylinux2014_x86_64"
DEPENDENCIES = ("pandas", "numpy", "pydantic", "fastapi", "mangum")
MAX_UNZIPPED_MB = 250  # limite de Lambda : fonction + couches, décompressées


def _size_mb(path: Path) -> float:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) / 1e6


def build_app() -> None:
    shutil.rmtree(APP, ignore_errors=True)
    shutil.copytree(REPO / "backend" / "easytrade", APP / "easytrade",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def build_layer() -> None:
    shutil.rmtree(LAYER.parent, ignore_errors=True)
    LAYER.mkdir(parents=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
        "--platform", PLATFORM, "--implementation", "cp", "--python-version", PYTHON_VERSION,
        "--only-binary=:all:", "--target", str(LAYER), *DEPENDENCIES,
    ], check=True)
    # Allègement : tests embarqués des bibliothèques et caches, jamais importés à l'exécution.
    for package in ("pandas", "numpy"):
        for tests in (LAYER / package).rglob("tests"):
            if tests.is_dir():
                shutil.rmtree(tests, ignore_errors=True)
    for cache in LAYER.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def main() -> int:
    build_app()
    build_layer()
    app_mb, layer_mb = _size_mb(APP), _size_mb(LAYER)
    print(f"Code : {app_mb:.1f} Mo · dépendances : {layer_mb:.1f} Mo · total {app_mb + layer_mb:.1f} Mo "
          f"(limite Lambda : {MAX_UNZIPPED_MB} Mo décompressés)")
    if app_mb + layer_mb > MAX_UNZIPPED_MB:
        print("Trop volumineux pour Lambda.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
