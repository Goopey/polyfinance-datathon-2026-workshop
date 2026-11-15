"""Point d'entrée CDK : instancie les piles.

Conception : docs/06_AWS.md, infra/README.md
    python build_lambda.py                      # une fois, puis après chaque changement du backend
    npx aws-cdk deploy --all -c bedrock_model_fast=<id> -c bedrock_model_strong=<id>
Région : us-east-1 (compte du datathon). Sans identifiants de modèles, les agents sont simulés.
"""
from __future__ import annotations

import os
import sys

import aws_cdk as cdk

from stacks.api_stack import ApiStack
from stacks.data_stack import DataStack
from stacks.pipeline_stack import BUILD, PipelineStack

if not (BUILD / "app" / "easytrade").exists() or not (BUILD / "layer" / "python").exists():
    raise SystemExit("Code des Lambda absent : lancer d'abord `python build_lambda.py` depuis infra/.")

app = cdk.App()
context = app.node.try_get_context
models = {
    "fast": context("bedrock_model_fast") or "",
    "strong": context("bedrock_model_strong") or "",
    "guardrail": context("bedrock_guardrail_id") or "",
}
if not (models["fast"] and models["strong"]):
    print("Attention : bedrock_model_fast / bedrock_model_strong non renseignés ; "
          "les agents seront simulés sur AWS.", file=sys.stderr)

env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=context("region") or "us-east-1")
data = DataStack(app, "EasyTradeData", env=env, description="EasyTrade — données et runs (S3, DynamoDB)")
pipeline = PipelineStack(app, "EasyTradePipeline", data=data, models=models, env=env,
                         description="EasyTrade — pipeline agentique (Lambda, Step Functions, Bedrock)")
ApiStack(app, "EasyTradeApi", data=data, pipeline=pipeline, models=models, env=env,
         description="EasyTrade — API (API Gateway, Lambda)")

# Étiquettes de coût sur toutes les ressources (docs/06_AWS.md, bonnes pratiques).
for key, value in {"projet": "easytrade", "evenement": "datathon-polyfinances-2026", "environnement": "workshop"}.items():
    cdk.Tags.of(app).add(key, value)

app.synth()
