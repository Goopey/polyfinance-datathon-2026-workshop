"""DataStack : compartiment S3 chiffré (données + runs), table DynamoDB (runs, profils fictifs).

Conception : docs/06_AWS.md
- S3 `data/` : jeu de départ et données de référence, copiés à chaque déploiement ; lus par les
  Lambda au démarrage à froid. S3 `runs/<run_id>/` : contexte entre deux étapes et artefacts JSON.
- DynamoDB : une table, clé `pk` (« RUN#… » : état et progression d'un run ; « PROFILE#… » : profil
  fictif créé par l'application).
Compte de démonstration temporaire : les ressources sont supprimées avec la pile (`cdk destroy`).
"""
from __future__ import annotations

from pathlib import Path

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

REPO = Path(__file__).resolve().parents[2]
DATA_PREFIX = "data/"


class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(
            self, "Donnees",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        for part in ("raw/starter", "reference"):
            s3deploy.BucketDeployment(
                self, "Copie-" + part.replace("/", "-"),
                sources=[s3deploy.Source.asset(str(REPO / "data" / part), exclude=["*.py", "README.md"])],
                destination_bucket=self.bucket,
                destination_key_prefix=f"{DATA_PREFIX}{part}/",
                prune=True,
            )

        self.table = dynamodb.Table(
            self, "Runs",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )
