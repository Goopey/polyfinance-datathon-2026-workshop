"""Recopie les données (jeu de départ, référence) vers le compartiment S3 du projet, sans redéployer.

Conception : docs/06_AWS.md, infra/README.md
Le déploiement CDK copie déjà ces données (`DataStack`). Ce script sert après une modification de
`data/raw/starter/` ou `data/reference/` (ex. arêtes du graphe, preuves ESG) :

    python scripts/seed_aws.py                       # nom du compartiment lu dans les sorties CloudFormation
    python scripts/seed_aws.py --bucket <nom>

Les Lambda déjà démarrées gardent leur copie en mémoire : les nouvelles données sont lues par les
conteneurs suivants (ou après `aws lambda update-function-configuration`, ou un redéploiement).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PARTS = ("raw/starter", "reference")
PREFIX = "data/"
SKIP = {"README.md"}


def find_bucket(cloudformation) -> str:
    resources = cloudformation.describe_stack_resources(StackName="EasyTradeData")["StackResources"]
    for resource in resources:
        if resource["ResourceType"] == "AWS::S3::Bucket":
            return resource["PhysicalResourceId"]
    raise SystemExit("Compartiment introuvable dans la pile EasyTradeData : déployer d'abord (infra/README.md).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bucket", help="nom du compartiment (défaut : celui de la pile EasyTradeData)")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args(argv)

    import boto3

    bucket = args.bucket or find_bucket(boto3.client("cloudformation", region_name=args.region))
    s3 = boto3.client("s3", region_name=args.region)
    sent = 0
    for part in PARTS:
        for path in sorted((REPO / "data" / part).rglob("*")):
            if path.is_file() and path.name not in SKIP and path.suffix != ".py":
                key = PREFIX + path.relative_to(REPO / "data").as_posix()
                s3.upload_file(str(path), bucket, key)
                sent += 1
    print(f"{sent} fichiers envoyés vers s3://{bucket}/{PREFIX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
