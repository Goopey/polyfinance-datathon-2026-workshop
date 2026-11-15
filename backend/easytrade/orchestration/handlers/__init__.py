"""Points d'entrée AWS Lambda, un par état de la machine d'états (infra/statemachine/pipeline.asl.json).

Conception : docs/06_AWS.md
    profile.handler          PonderationDuProfil     crée le contexte du run
    validation.handler       ValidationFinanciere
    research.handler         Recherche
    evidence_packs.handler   DossiersDePreuves       rend la liste des candidats à débattre
    debate.handler           ConseilDeDebat (Map)    un candidat par invocation
    decision.handler         MoteurDeDecision        rassemble les débats
    explanation.handler      Explication             termine le run
    failure.handler          MarquerEchec            chemin Catch
Chaque étape appelle la même fonction que `orchestration.pipeline.run_pipeline` en local.
`ingestion.py` (ingestion planifiée) reste un extra (docs/10_PLAN.md).
"""
