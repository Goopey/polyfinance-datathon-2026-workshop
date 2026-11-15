"""ApiStack : API Gateway (HTTP) et Lambda API (FastAPI + Mangum).

Conception : docs/06_AWS.md, docs/01_ARCHITECTURE.md (table des routes)
L'URL affichée en sortie (`ApiUrl`) est celle à mettre dans `mobile/.env` (`EXPO_PUBLIC_API_URL`).
Aucune route ne passe d'ordre : l'API lit des données datées et lance des analyses simulées.
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from stacks.data_stack import DataStack
from stacks.pipeline_stack import BUILD, PipelineStack, bedrock_policy, runtime_environment


class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, data: DataStack, pipeline: PipelineStack,
                 models: dict[str, str], **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Origines autorisées : `cdk deploy -c corsOrigins=https://mon-site.example` (séparées par des virgules).
        # Par défaut « * » (application Expo en développement) ; à restreindre pour la version hébergée.
        cors_origins = [o.strip() for o in str(self.node.try_get_context("corsOrigins") or "*").split(",") if o.strip()]
        environment = {
            **runtime_environment(data, models),
            "EASYTRADE_STATE_MACHINE_ARN": pipeline.state_machine.state_machine_arn,
            "EASYTRADE_CORS_ORIGINS": ",".join(cors_origins),
            # Appel Bedrock synchrone (GET /profiles/{id}) : doit tenir sous la limite de 29 s de l'intégration.
            "EASYTRADE_BEDROCK_READ_TIMEOUT": "20",
            "EASYTRADE_BEDROCK_MAX_ATTEMPTS": "1",
        }
        log_group = logs.LogGroup(self, "JournauxApi", retention=logs.RetentionDays.TWO_WEEKS,
                                  removal_policy=RemovalPolicy.DESTROY)
        fn = lambda_.Function(
            self, "Api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            handler="easytrade.api.app.handler",
            code=lambda_.Code.from_asset(str(BUILD / "app")),
            # Couche propre à cette pile (même paquet que la pile du pipeline) : partager la couche entre
            # deux piles crée un export CloudFormation qui bloque tout redéploiement après reconstruction.
            layers=[lambda_.LayerVersion(
                self, "Dependances",
                code=lambda_.Code.from_asset(str(BUILD / "layer")),
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
                compatible_architectures=[lambda_.Architecture.X86_64],
                description="pandas, numpy, pydantic, fastapi, mangum (infra/build_lambda.py)",
            )],
            memory_size=2048,
            timeout=Duration.seconds(29),  # limite d'une intégration API Gateway HTTP
            environment=environment,
            log_group=log_group,
            description="EasyTrade — API (FastAPI)",
        )
        data.bucket.grant_read(fn)
        data.table.grant_read_write_data(fn)
        pipeline.state_machine.grant_start_execution(fn)
        fn.add_to_role_policy(bedrock_policy(self))  # GET /profiles/{id} : pondération du profil par l'agent

        http = apigw.HttpApi(
            self, "HttpApi",
            description="EasyTrade — simulateur d'aide à la décision (aucune transaction réelle)",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=cors_origins,
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                allow_headers=["*"],
                max_age=Duration.hours(1),
            ),
            default_integration=integrations.HttpLambdaIntegration("Lambda", fn),
        )
        # Limite de débit de l'étape par défaut : chaque analyse déclenche des appels Bedrock payants ; une URL
        # publique sans limite exposerait le compte à un emballement des coûts (audit H4).
        stage = http.default_stage.node.default_child
        stage.default_route_settings = apigw.CfnStage.RouteSettingsProperty(
            throttling_rate_limit=5, throttling_burst_limit=10)
        CfnOutput(self, "ApiUrl", value=http.api_endpoint, description="À mettre dans mobile/.env : EXPO_PUBLIC_API_URL")
        CfnOutput(self, "StateMachineArn", value=pipeline.state_machine.state_machine_arn)
