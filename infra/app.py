"""Point d'entrée CDK : instancie les piles.

Conception : docs/06_AWS.md, infra/README.md
    python build_lambda.py      # après chaque changement du backend
    python build_web.py         # après chaque changement de l'application (URL de l'API figée dedans)
    npx.cmd aws-cdk deploy --all --require-approval never
Région : us-east-1 (compte du datathon). Modèles Bedrock : cdk.json. Sans eux, les agents sont simulés.
Sans `build/web/`, la pile du site (EasyTradeWeb) n'est pas déployée ; les autres le sont.
"""
from __future__ import annotations

import os
import sys

import aws_cdk as cdk

from stacks.api_stack import ApiStack
from stacks.data_stack import DataStack
from stacks.frontend_stack import WEB, FrontendStack
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
if (WEB / "index.html").exists():
    FrontendStack(app, "EasyTradeWeb", env=env, description="EasyTrade — application web (S3, CloudFront)")
else:
    print("Site web absent (infra/build/web) : lancer `python build_web.py` pour déployer aussi l'application.",
          file=sys.stderr)

# Étiquettes de coût sur toutes les ressources (docs/06_AWS.md, bonnes pratiques).
for key, value in {"projet": "easytrade", "evenement": "datathon-polyfinances-2026", "environnement": "workshop"}.items():
    cdk.Tags.of(app).add(key, value)

app.synth()
