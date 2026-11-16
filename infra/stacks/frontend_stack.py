"""FrontendStack : version web de l'application (Expo) servie par CloudFront depuis un compartiment privé.

Conception : docs/06_AWS.md, infra/README.md
- Le site est construit par `infra/build_web.py` (URL de l'API figée dans le paquet) dans `infra/build/web/`.
- Compartiment S3 privé (accès public bloqué) ; seul CloudFront le lit (contrôle d'accès d'origine).
- Application à page unique : toute adresse inconnue (/piste/AAPL, /run/…) renvoie `index.html`, et le
  routeur de l'application affiche le bon écran.
- Chaque déploiement envoie la nouvelle version et invalide le cache de CloudFront.
L'URL publique est la sortie `WebUrl` : c'est l'adresse à donner pour essayer l'application.
"""
from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

WEB = Path(__file__).resolve().parents[1] / "build" / "web"


class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(
            self, "Site",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        spa = [
            cloudfront.ErrorResponse(http_status=status, response_http_status=200, response_page_path="/index.html",
                                     ttl=Duration.seconds(0))
            for status in (403, 404)
        ]
        distribution = cloudfront.Distribution(
            self, "Distribution",
            comment="EasyTrade — application web (simulation, aucune transaction réelle)",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            error_responses=spa,
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )
        s3deploy.BucketDeployment(
            self, "Envoi",
            sources=[s3deploy.Source.asset(str(WEB))],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
            prune=True,
            memory_limit=512,
        )
        CfnOutput(self, "WebUrl", value=f"https://{distribution.distribution_domain_name}",
                  description="Adresse publique de l'application web")
