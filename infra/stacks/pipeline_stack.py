"""PipelineStack : une Lambda par étape, machine d'états, rôles IAM à privilège minimal, accès Bedrock.

Conception : docs/06_AWS.md, infra/statemachine/pipeline.asl.json
Chaque fonction a son propre rôle : lecture et écriture du compartiment et de la table du projet,
Bedrock seulement pour les étapes qui appellent un modèle. Aucune clé dans le code : Bedrock est
appelé avec le rôle de la fonction.
"""
from __future__ import annotations

from pathlib import Path

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as sfn
from constructs import Construct

from stacks.data_stack import DATA_PREFIX, DataStack

INFRA = Path(__file__).resolve().parents[1]
BUILD = INFRA / "build"
ASL = INFRA / "statemachine" / "pipeline.asl.json"
HANDLERS = "easytrade.orchestration.handlers"

# Clé de substitution de l'ASL → (module du handler, délai en secondes, appelle Bedrock)
STEPS: dict[str, tuple[str, int, bool]] = {
    "Profile": ("profile", 300, True),
    "Validation": ("validation", 180, False),
    "Research": ("research", 600, True),
    "EvidencePacks": ("evidence_packs", 180, False),
    "Debate": ("debate", 600, True),
    "Decision": ("decision", 180, False),
    "Explanation": ("explanation", 600, True),
    "Failure": ("failure", 60, False),
}


def bedrock_policy(stack: Stack) -> iam.PolicyStatement:
    """Appel des modèles et des profils d'inférence interrégionaux (« us.… », routés vers d'autres régions)."""
    return iam.PolicyStatement(
        actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:ApplyGuardrail"],
        resources=[
            "arn:aws:bedrock:*::foundation-model/*",
            f"arn:aws:bedrock:*:{stack.account}:inference-profile/*",
            f"arn:aws:bedrock:*:{stack.account}:application-inference-profile/*",
            f"arn:aws:bedrock:{stack.region}:{stack.account}:guardrail/*",
        ],
    )


def runtime_environment(data: DataStack, models: dict[str, str]) -> dict[str, str]:
    env = {
        "EASYTRADE_ENV": "aws",
        "EASYTRADE_DATA_BUCKET": data.bucket.bucket_name,
        "EASYTRADE_DATA_PREFIX": DATA_PREFIX,
        "EASYTRADE_STATE_BUCKET": data.bucket.bucket_name,
        "EASYTRADE_TABLE": data.table.table_name,
        "EASYTRADE_DEBATE_WORKERS": "3",
    }
    # Sans identifiants de modèles, les agents sont simulés (la trace et l'explication le disent).
    if models.get("fast") and models.get("strong"):
        env["BEDROCK_MODEL_ID_FAST"], env["BEDROCK_MODEL_ID_STRONG"] = models["fast"], models["strong"]
    if models.get("guardrail"):
        env["BEDROCK_GUARDRAIL_ID"] = models["guardrail"]
    return env


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, data: DataStack, models: dict[str, str],
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.layer = lambda_.LayerVersion(
            self, "Dependances",
            code=lambda_.Code.from_asset(str(BUILD / "layer")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.X86_64],
            description="pandas, numpy, pydantic, fastapi, mangum (infra/build_lambda.py)",
        )
        self.code = lambda_.Code.from_asset(str(BUILD / "app"))
        environment = runtime_environment(data, models)

        functions: dict[str, lambda_.Function] = {}
        for key, (module, timeout, uses_bedrock) in STEPS.items():
            log_group = logs.LogGroup(self, f"Journaux{key}", retention=logs.RetentionDays.TWO_WEEKS,
                                      removal_policy=RemovalPolicy.DESTROY)
            fn = lambda_.Function(
                self, f"Etape{key}",
                runtime=lambda_.Runtime.PYTHON_3_12,
                architecture=lambda_.Architecture.X86_64,
                handler=f"{HANDLERS}.{module}.handler",
                code=self.code,
                layers=[self.layer],
                memory_size=2048,
                timeout=Duration.seconds(timeout),
                environment=environment,
                log_group=log_group,
                description=f"EasyTrade — étape {module} du pipeline",
            )
            data.bucket.grant_read_write(fn)
            data.table.grant_read_write_data(fn)
            if uses_bedrock:
                fn.add_to_role_policy(bedrock_policy(self))
            functions[key] = fn

        machine_logs = logs.LogGroup(self, "JournauxMachine", retention=logs.RetentionDays.TWO_WEEKS,
                                     removal_policy=RemovalPolicy.DESTROY)
        self.state_machine = sfn.StateMachine(
            self, "Pipeline",
            definition_body=sfn.DefinitionBody.from_file(str(ASL)),
            definition_substitutions={f"{key}FunctionArn": fn.function_arn for key, fn in functions.items()},
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.minutes(45),
            tracing_enabled=True,
            logs=sfn.LogOptions(destination=machine_logs, level=sfn.LogLevel.ERROR),
        )
        for fn in functions.values():
            fn.grant_invoke(self.state_machine)
        self.functions = functions
