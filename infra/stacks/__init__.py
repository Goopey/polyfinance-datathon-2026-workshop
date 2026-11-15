"""Piles CDK (docs/06_AWS.md).

    DataStack       S3 (données, runs), DynamoDB (runs, profils fictifs)
    PipelineStack   Lambda par étape, Step Functions, accès Bedrock
    ApiStack        API Gateway HTTP + Lambda API
IngestionStack et FrontendStack restent des extras (docs/10_PLAN.md).
"""
