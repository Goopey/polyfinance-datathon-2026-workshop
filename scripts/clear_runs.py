"""Vide les analyses enregistrées sur AWS (avant de les recalculer après un changement du moteur).

Conception : docs/06_AWS.md (section « Précalcul »), infra/README.md
Les analyses précalculées ne se mettent pas à jour seules : le pipeline est déterministe et l'API
sert un run terminé de même identifiant sans le refaire. Après un changement du moteur, des données,
des modèles ou des invites, il faut donc les supprimer, puis relancer `scripts/precompute.py`.

    python scripts/clear_runs.py                       # montre ce qui serait supprimé, ne supprime rien
    python scripts/clear_runs.py --yes                 # supprime toutes les analyses (table + S3)
    python scripts/clear_runs.py --run run_2026-11-12_robert --yes
    python scripts/clear_runs.py --views --yes         # supprime aussi les vues de profil (agent de pondération)

Supprime dans la table DynamoDB les lignes « RUN#… » (et « VIEW#… » avec --views) et, sur S3, les
dossiers `runs/<run_id>/`. Ne touche ni aux données (`data/`), ni aux profils fictifs (« PROFILE#… »).
Le compartiment et la table sont lus dans la pile CloudFormation `EasyTradeData`. Identifiants AWS :
ceux du terminal (charger `.env` d'abord).
"""
from __future__ import annotations

import argparse
import sys

STACK = "EasyTradeData"


def stack_resources(cloudformation) -> tuple[str, str]:
    resources = cloudformation.describe_stack_resources(StackName=STACK)["StackResources"]
    by_type = {r["ResourceType"]: r["PhysicalResourceId"] for r in resources}
    try:
        return by_type["AWS::S3::Bucket"], by_type["AWS::DynamoDB::Table"]
    except KeyError as error:
        raise SystemExit(f"Ressource introuvable dans la pile {STACK} : {error}") from error


def table_keys(dynamodb, table: str, prefixes: tuple[str, ...]) -> list[str]:
    keys: list[str] = []
    kwargs = {"TableName": table, "ProjectionExpression": "pk"}
    while True:
        page = dynamodb.scan(**kwargs)
        keys.extend(item["pk"]["S"] for item in page.get("Items", []) if item["pk"]["S"].startswith(prefixes))
        if "LastEvaluatedKey" not in page:
            return sorted(keys)
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def run_objects(s3, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--yes", action="store_true", help="supprimer vraiment (sinon : affichage seulement)")
    parser.add_argument("--run", help="un seul run (ex. run_2026-11-12_robert) ; défaut : tous")
    parser.add_argument("--views", action="store_true", help="supprimer aussi les vues de profil (VIEW#…)")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    import boto3

    bucket, table = stack_resources(boto3.client("cloudformation", region_name=args.region))
    dynamodb = boto3.client("dynamodb", region_name=args.region)
    s3 = boto3.client("s3", region_name=args.region)

    prefixes = (f"RUN#{args.run}",) if args.run else ("RUN#",)
    if args.views:
        prefixes += ("VIEW#",)
    rows = table_keys(dynamodb, table, prefixes)
    objects = run_objects(s3, bucket, f"runs/{args.run}/" if args.run else "runs/")

    print(f"Table {table} : {len(rows)} ligne(s) — " + (", ".join(rows) if rows else "aucune"))
    print(f"Compartiment {bucket} : {len(objects)} fichier(s) sous runs/")
    if not args.yes:
        print("\nRien n'a été supprimé. Relancer avec --yes pour supprimer.")
        return 0

    for key in rows:
        dynamodb.delete_item(TableName=table, Key={"pk": {"S": key}})
    for start in range(0, len(objects), 1000):  # 1 000 objets au plus par requête
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in objects[start:start + 1000]]})
    left = table_keys(dynamodb, table, prefixes)
    print(f"\nSupprimé : {len(rows)} ligne(s), {len(objects)} fichier(s). Restant dans la table : {len(left)}.")
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main())
