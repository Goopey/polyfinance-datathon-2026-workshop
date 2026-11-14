# Infrastructure (AWS CDK, Python)

Conception : `docs/06_AWS.md`.

```bash
cd infra && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap        # une fois par compte et région
cdk deploy DataStack PipelineStack ApiStack
```

À confirmer avant le premier déploiement : services autorisés, région et modèles Bedrock du compte fourni par le datathon.

| Pile | Contenu |
|---|---|
| `DataStack` | S3 (raw, curated, runs), DynamoDB (profiles, runs, evidence, graph_edges) |
| `PipelineStack` | Lambda des étapes, machine d'états (`statemachine/pipeline.asl.json`), droits Bedrock |
| `ApiStack` | API Gateway + Lambda API |
| `IngestionStack` | EventBridge Scheduler, Lambda d'ingestion, Secrets Manager |
| `FrontendStack` | Hébergement de la version web (extra) |
