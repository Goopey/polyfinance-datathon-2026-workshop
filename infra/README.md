# Infrastructure (AWS CDK, Python)

Conception : `docs/06_AWS.md`. Compte du datathon : **compte d'atelier temporaire, région `us-east-1`**.

## Ce qui est déployé

```
Mobile ─► API Gateway (HTTP) ─► Lambda API (FastAPI) ─► DynamoDB (runs, profils fictifs)
                                     │ StartExecution
                                     ▼
  Step Functions : Profil → Validation → Recherche → Dossiers de preuves → Débat (Map, 1 Lambda par candidat)
                   → Décision → Explication            (échec → MarquerEchec → AnalyseEchouee)
                                     │
                                     ▼
  S3 : data/ (jeu de départ, référence)  ·  runs/<run_id>/ (contexte entre étapes, artefacts JSON)
  Bedrock : appelé par les étapes Profil, Recherche, Débat, Explication et par l'API (pondération)
```

| Pile | Contenu |
|---|---|
| `EasyTradeData` | Compartiment S3 chiffré (données copiées au déploiement), table DynamoDB |
| `EasyTradePipeline` | 8 Lambda (une par état), couche de dépendances, machine d'états (`statemachine/pipeline.asl.json`), un rôle IAM par fonction, Bedrock pour les étapes à modèle |
| `EasyTradeApi` | API Gateway HTTP + Lambda API ; sortie `ApiUrl` |
| `IngestionStack`, `FrontendStack` | Extras, non déployés (squelettes) |

Les étapes sont en série : les identifiants de preuves (`EV-000001`…) restent reproductibles, et le
résultat sur AWS est identique au pipeline local (vérifié par `backend/tests/aws`).

## Déployer (à faire par l'équipe, avec le compte d'atelier)

Prérequis : Python ≥ 3.11, Node (déjà installé), AWS CLI v2.

1. **Identifiants.** Copier les identifiants temporaires depuis la page de l'atelier (ils expirent :
   les recopier quand une commande échoue avec `ExpiredToken`). Vérifier :
   ```bash
   aws sts get-caller-identity
   ```
   Créer une **alerte de budget** (AWS Budgets) avant tout déploiement.
2. **Modèles Bedrock.** Console Bedrock, région us-east-1 → *Model access* : ouvrir un modèle rapide
   (ex. Claude Haiku 5.5) et un modèle fort (ex. Claude Sonnet 5.5 ou Opus 5.5). Copier leurs
   identifiants exacts depuis le catalogue (profil d'inférence, souvent `us.anthropic.…`).
3. **Construire le code des Lambda** (sans Docker ; à refaire après chaque changement du backend) :
   ```bash
   cd infra
   pip install -r requirements.txt
   python build_lambda.py
   ```
4. **Déployer** :
   ```bash
   npx aws-cdk bootstrap                     # une fois par compte et région
   npx aws-cdk deploy --all -c bedrock_model_fast=<id rapide> -c bedrock_model_strong=<id fort>
   ```
   Sans les deux identifiants, tout est déployé mais les agents sont simulés (la trace le dit).
   Si `bootstrap` est refusé, le compte d'atelier bloque la création de rôles IAM : le signaler aux
   organisateurs.
5. **Tester** : l'URL est dans la sortie `EasyTradeApi.ApiUrl`.
   ```bash
   curl <ApiUrl>/health
   curl -X POST <ApiUrl>/runs -H "Content-Type: application/json" -d '{"profile_id":"robert","requested_ticker":"TSLA"}'
   curl <ApiUrl>/runs/run_2026-11-12_robert_TSLA
   ```
   Suivre l'exécution dans la console Step Functions (graphe en direct : capture pour la vidéo, tâche E4).
6. **Précalculer les analyses** (réponse en moins d'une seconde ensuite) :
   ```bash
   python scripts/precompute.py --api <ApiUrl>                  # 3 personas + 3 × 31 « Tester une idée »
   python scripts/precompute.py --api <ApiUrl> --tickers none   # essai : seulement les 3 analyses par défaut
   ```
   Une analyse en direct prend 1,5 à 2 minutes (une trentaine d'appels aux modèles) ; le moteur seul,
   0,3 seconde. L'identifiant d'un run ne dépend que de la date, du profil et du titre : une fois calculé,
   il est servi tel quel. Tout précalculer : environ 96 analyses, 35 à 60 $ (estimation), 30 à 60 minutes
   avec 3 analyses à la fois. Relancer le script ne refait que ce qui manque ou a échoué.
7. **Brancher le mobile** : dans `mobile/.env`, `EXPO_PUBLIC_API_URL=<ApiUrl>` et `EXPO_PUBLIC_USE_MOCKS=false`.

Après une modification de `data/` sans changement de code : `python scripts/seed_aws.py`.
Fin de l'atelier : `npx aws-cdk destroy --all` (le compte sera de toute façon supprimé).

## Coût

Lambda, Step Functions, DynamoDB à la demande et API Gateway : quelques centimes pour une démonstration.
Le poste principal est Bedrock (environ 0,35 à 0,60 $ par analyse complète selon le modèle fort,
estimation). Pas de VPC ni de passerelle NAT. Toutes les ressources portent les étiquettes `projet`,
`evenement`, `environnement`.

## Sécurité

- Un rôle IAM par fonction, limité au compartiment et à la table du projet ; Bedrock seulement pour
  les étapes qui appellent un modèle ; l'API peut seulement démarrer la machine d'états.
- Aucun secret : Bedrock est appelé avec le rôle de la fonction (pas de clé). Secrets Manager servira
  si une API tierce (Finnhub, Alpaca) est activée.
- S3 : chiffrement, accès public bloqué, TLS obligatoire. DynamoDB : chiffrement géré par AWS.
- Le contexte d'un run est sérialisé (`pickle`) et n'est lu que par nos fonctions, dans ce compartiment privé.
