"""Construit la version web de l'application (Expo) pour l'hébergement sur AWS (FrontendStack).

Conception : docs/06_AWS.md, infra/README.md
À lancer depuis `infra/`, avant `cdk deploy`, chaque fois que l'application ou l'URL de l'API change :

    python build_web.py                 # URL de l'API : EASYTRADE_API_URL (.env), sinon sortie de la pile EasyTradeApi

L'URL de l'API est **figée dans le paquet** au moment de la construction (variables `EXPO_PUBLIC_*` d'Expo) :
le site appelle l'API déployée, jamais les données fictives. Résultat : `infra/build/web/` (page unique).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parent
REPO = INFRA.parent
MOBILE = REPO / "mobile"
OUT = INFRA / "build" / "web"


def api_url() -> str:
    url = os.environ.get("EASYTRADE_API_URL", "").strip()
    if not url:
        try:
            import boto3

            outputs = boto3.client("cloudformation", region_name="us-east-1").describe_stacks(
                StackName="EasyTradeApi")["Stacks"][0].get("Outputs", [])
            url = next((o["OutputValue"] for o in outputs if o["OutputKey"] == "ApiUrl"), "")
        except Exception as error:  # identifiants absents, pile non déployée
            print(f"Sortie ApiUrl illisible : {error}", file=sys.stderr)
    if not url:
        raise SystemExit("URL de l'API inconnue : mettre EASYTRADE_API_URL dans .env (charger .env), "
                         "ou déployer d'abord la pile EasyTradeApi.")
    return url.rstrip("/")


def main() -> int:
    url = api_url()
    if not (MOBILE / "node_modules").exists():
        raise SystemExit("mobile/node_modules absent : lancer `npm install` dans mobile/ d'abord.")
    shutil.rmtree(OUT, ignore_errors=True)
    env = {**os.environ, "EXPO_PUBLIC_API_URL": url, "EXPO_PUBLIC_USE_MOCKS": "false", "CI": "1"}
    command = f'npx expo export --platform web --output-dir "{OUT}" --clear'
    print(f"Construction du site pour l'API {url} …")
    done = subprocess.run(command, cwd=MOBILE, env=env, shell=True)
    if done.returncode != 0 or not (OUT / "index.html").exists():
        print("Export web en échec (voir les messages d'Expo ci-dessus).", file=sys.stderr)
        return 1
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"Site prêt : {OUT} ({size:.1f} Mo). Étape suivante : npx.cmd aws-cdk deploy --all --require-approval never")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
