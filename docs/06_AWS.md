# 06 — Intégration AWS

Deux consignes à tenir ensemble :

- **Admissibilité** : AWS doit contribuer réellement et de manière démontrable au fonctionnement de la solution. Sans intégration effective, le projet n'est pas évalué.
- **« Ne multipliez pas les services pour impressionner. Justifiez chaque choix. »** (présentation officielle). Le conseil d'un ancien gagnant, exploiter beaucoup de services, n'est valable que si chaque service a un rôle montré en démo.

Règle d'équipe : **un service entre dans l'architecture seulement s'il a une ligne complète dans le tableau ci-dessous**, colonne « Visible en démo » comprise.

## Services retenus

| Service | Rôle dans EasyTrade | Pourquoi celui-ci | Visible en démo | Niveau |
|---|---|---|---|---|
| Amazon Bedrock | Modèles des agents (profil, recherche, débat, explication) | Accès aux modèles sans gérer d'infrastructure | Trace : modèle utilisé à chaque étape | MVP |
| AWS Step Functions | Orchestration du pipeline : parallèle Recherche ∥ Validation, `Map` sur les 3 débatteurs | Le graphe d'exécution **est** notre diagramme agentique ; historique auditable | Capture de l'exécution en direct | MVP |
| AWS Lambda | Une fonction par étape + API + ingestion | Sans serveur, coût faible, même code qu'en local | Durée par étape dans la trace | MVP |
| Amazon API Gateway | Point d'entrée HTTPS du mobile | Standard, limitation de débit | L'application appelle une URL AWS | MVP |
| Amazon S3 | Données brutes, préparées, artefacts de chaque run | Stockage durable, versionné | Lien vers l'artefact d'une preuve | MVP |
| Amazon DynamoDB | Profils, runs, registre de preuves, arêtes du graphe | Lecture par clé rapide pour le mobile | Écran « Pourquoi ? » | MVP |
| Amazon CloudWatch | Journaux et métriques des étapes | Observabilité, validation | Tableau de bord court dans la vidéo | MVP |
| AWS IAM + Secrets Manager | Rôles à privilège minimal par fonction ; clés d'API hors du code | Bonnes pratiques attendues par la grille | Mention dans la documentation | MVP |
| Amazon Bedrock Guardrails | Refus des formulations de type conseil personnalisé dans l'explication | Gouvernance visible | Exemple de phrase bloquée | Extra n° 1 |
| Amazon EventBridge Scheduler | Ingestion planifiée des données | Fraîcheur, instantanés datés | Mention + règle visible | Extra n° 2 |
| AWS Amplify Hosting (ou S3 + CloudFront) | Version web de l'application Expo pour le jury | Le jury teste sans installer d'application | Lien public | Extra n° 3 |
| Bedrock Knowledge Bases | Recherche dans les dépôts et rapports ESG avec citations | Citations de passages | Citation cliquable | Extra n° 4 |
| Amazon Athena | Requêtes SQL sur les données préparées | Démonstration de la rigueur des données | Requête de contrôle qualité | Extra n° 5 |

## Services écartés

| Service | Raison |
|---|---|
| Amazon Neptune | Le graphe compte quelques dizaines de nœuds : une liste d'adjacence dans DynamoDB suffit. Coût et temps de mise en place non justifiés. |
| Amazon Cognito | Les profils sont fictifs, pas de compte réel. À reconsidérer seulement si le temps le permet. |
| Amazon SageMaker | Aucun modèle entraîné ; on ne prédit pas de rendement. |

## Architecture cible

```
                    ┌────────────┐      ┌──────────────────────┐
   Mobile / Web ───►│ API Gateway│─────►│ Lambda API (FastAPI) │
                    └────────────┘      └──────────┬───────────┘
                                                   │ StartExecution
                                                   ▼
        ┌───────────────────────── Step Functions ─────────────────────────┐
        │  Profil ─► ┌ Recherche ┐ ─► Débat (Map ×3) ─► Décision ─► Explication │
        │            └ Validation┘                                          │
        └───────┬───────────────┬──────────────────────────────┬───────────┘
                │               │                              │
           ┌────▼────┐     ┌────▼─────┐                  ┌─────▼──────┐
           │ Bedrock │     │ DynamoDB │                  │     S3     │
           │ (+Guard-│     │ runs,    │                  │ raw/curated│
           │  rails) │     │ preuves  │                  │ /runs      │
           └─────────┘     └──────────┘                  └─────▲──────┘
                                                               │
                       EventBridge Scheduler ─► Lambda ingestion
        CloudWatch : journaux et métriques de toutes les fonctions
```

## Orchestration des agents : choix et alternative

- **Retenu** : Step Functions orchestre les étapes ; chaque agent LLM est un appel Bedrock à sortie structurée. L'agent de recherche, qui choisit ses outils, peut être écrit avec le SDK Strands Agents.
- **Alternative** : héberger les agents sur Amazon Bedrock AgentCore. Plus « natif agents », mais plus d'inconnues pour un hackathon.
- À ne pas utiliser pour un nouveau projet : l'ancienne fonctionnalité « Bedrock Agents » (classique), en fin de parcours pour les nouveaux clients d'après les annonces AWS de 2026.

Voir `adr/0003-orchestration-step-functions-bedrock.md`.

## Infrastructure comme code

AWS CDK en Python, dans `infra/`. Une pile par domaine pour pouvoir déployer par morceaux :

| Pile | Contenu |
|---|---|
| `DataStack` | Compartiments S3, tables DynamoDB |
| `PipelineStack` | Lambda des étapes, machine d'états, droits Bedrock |
| `ApiStack` | API Gateway, Lambda API |
| `IngestionStack` | Planification, Lambda d'ingestion, secrets |
| `FrontendStack` | Hébergement de la version web |

## Bonnes pratiques à montrer

- Un rôle IAM par fonction, droits limités aux ressources utilisées.
- Aucune clé dans le dépôt : `.env.example` en local, Secrets Manager sur AWS.
- Chiffrement par défaut de S3 et DynamoDB.
- Étiquettes de coût sur toutes les ressources ; estimation du coût d'une analyse dans la documentation.
- Délais d'expiration et relances configurés dans Step Functions ; échec propre d'une étape visible dans la trace.

## Réalisation (P4)

Code prêt à déployer ; déploiement et premier run sur le compte d'atelier : tâche E4. Commandes : `infra/README.md`.

- **Étapes en série** : Profil → Validation → Recherche → Dossiers de preuves → Débat → Décision → Explication.
  La branche parallèle Recherche ∥ Validation du schéma d'origine est abandonnée : les deux étapes ajoutent des
  preuves au registre, et des écritures concurrentes rendraient les identifiants (`EV-000001`…) non reproductibles.
- **Débat en état `Map`** : une Lambda par candidat, quatre en parallèle. Possible parce que le débat lit le
  registre sans y écrire (`clean_turn` → `check_claim`).
- **Même code qu'en local** : `orchestration/pipeline.py` est découpé en fonctions d'étape (`stage_*`) qui
  partagent un `RunContext` ; `run_pipeline` les enchaîne en local, chaque Lambda en exécute une sur AWS. Le
  contexte est enregistré sur S3 entre deux étapes. `backend/tests/aws` exécute la vraie machine d'états
  (interprétée) et vérifie un résultat identique au pipeline local.
- **Erreurs** : Bedrock indisponible → relances par Step Functions depuis le dernier point enregistré ; autre
  erreur → run marqué « echec », trace à l'appui, sans relance ; délai dépassé → `MarquerEchec`.
- **Écart avec le tableau ci-dessus** : le registre de preuves est servi depuis l'artefact du run sur S3, pas
  depuis DynamoDB. DynamoDB porte l'état et la progression des runs et les profils fictifs. Arêtes du graphe :
  fichier de référence copié sur S3.
- **Modèles** (au choix de l'équipe, budget 500 $) : rapide pour le débat (ex. Claude Haiku 5.5), fort pour le
  profil, la recherche et l'explication (ex. Claude Sonnet 5.5 ou Opus 5.5). Le client Converse n'envoie ni
  `temperature` ni `toolChoice` forcé, refusés par ces modèles.

## Précalcul : réponse en moins d'une seconde

Mesures : le moteur seul (validation, dossiers, score, décision, sur les 31 actifs) prend **0,3 s** ; une
analyse avec les agents enchaîne au moins cinq appels au modèle qui dépendent les uns des autres (profil →
recherche → débat tour 1 → tour 3 → explication), soit 8 à 15 s au mieux et 1,5 à 2 min en pratique (une
trentaine d'appels de 8 à 12 s). Le direct ne peut donc pas tenir l'objectif de 5 secondes.

Choix : les agents sont **précalculés** (`scripts/precompute.py`). Le pipeline est déterministe et
l'identifiant d'un run ne dépend que de la date, du profil et du titre demandé ; l'API sert un run terminé
de même identifiant sans le refaire. On calcule donc une fois, sur AWS, les analyses par défaut des
personas et « Tester une idée » pour chaque persona × chaque titre (96 analyses), plus la vue pondérée de
chaque profil (gardée dans DynamoDB, `VIEW#<id>`). C'est conforme à l'ADR 0001 : le code décide, les agents
argumentent ; leur travail est fait en amont, toujours tracé et daté.

Limites : un profil fictif créé par questionnaire, ou une autre date de référence, n'est pas précalculé :
l'analyse tourne alors en direct (1,5 à 2 min sur AWS, avec l'écran de progression). Le débat d'un run en
direct est parallèle (état `Map` sur AWS ; `candidate_workers` en local).

## Points confirmés (A2, 2026-11-14)

Compte d'atelier temporaire, région **us-east-1**, Amazon Bedrock, modèles au choix de l'équipe, **500 $ de
crédits**. Encore à vérifier sur le compte : que Lambda, Step Functions, API Gateway, S3 et DynamoDB sont
ouverts, et que `cdk bootstrap` peut créer des rôles IAM.

## À confirmer dès que possible (état d'origine)

1. Type de compte AWS fourni par le datathon et **services autorisés**.
2. Région imposée et modèles Bedrock ouverts dans ce compte.
3. Budget ou crédits disponibles.
4. Exigences d'infrastructure des consignes logistiques officielles.

Tant que le point 1 n'est pas levé, on développe en local avec `orchestration/pipeline.py` et des appels Bedrock isolés derrière une interface (`agents/llm_client.py`).
