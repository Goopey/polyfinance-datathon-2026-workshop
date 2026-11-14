# 01 — Architecture

Le diagramme d'origine de l'équipe est conservé dans `diagrammes/architecture_agentique.txt`. Ce document le traduit en modules, contrats et services.

## Vue d'ensemble

```
 Mobile (Expo / React Native)                       AWS
┌──────────────────────────┐   HTTPS   ┌──────────────────────────────────────────────┐
│ Profil → Pistes → Fiche  │ ────────► │ API Gateway ─► Lambda API (FastAPI)          │
│ Tester une idée          │ ◄──────── │        │ démarre / interroge une exécution   │
│ Pourquoi ? (preuves)     │  polling  │        ▼                                     │
└──────────────────────────┘           │ Step Functions : pipeline d'analyse          │
                                       │  1 Profil ─► [2 Recherche ∥ Validation]      │
                                       │    ─► 3 Débat (Bull ∥ Réaliste ∥ Bear)       │
                                       │    ─► 4 Moteur de décision ─► 5 Explication  │
                                       │        │                │                    │
                                       │   Bedrock (LLM)   DynamoDB (runs, preuves)   │
                                       │        │                │                    │
                                       │   S3 (données brutes / préparées / runs)     │
                                       └──────────────────────────────────────────────┘
        Ingestion planifiée : EventBridge Scheduler ─► Lambda d'ingestion ─► S3
```

## Du diagramme aux modules

| Bloc du diagramme | Nature | Module backend | Exécution AWS |
|---|---|---|---|
| Investor Profile | Donnée | `schemas/profile.py`, `data/reference/personas.json` | DynamoDB `profiles` |
| 1. Profile Weighting Agent | LLM + règles | `agents/profile_weighting.py` | Lambda + Bedrock |
| 2. Investment Research Agent | LLM avec outils | `agents/research.py` | Lambda + Bedrock |
| Financial Validation Layer | **Python déterministe** | `validation/` | Lambda (aucun LLM) |
| 3. Debate Council | 3 LLM, mêmes preuves | `agents/debate/` | Step Functions `Map` + Bedrock |
| Debate Protocol | Orchestration | `agents/debate/protocol.py` | Step Functions |
| 4. Decision Engine | **Python déterministe** | `engine/` | Lambda (aucun LLM) |
| 5. Explanation Agent | LLM contraint par les preuves | `agents/explanation.py` + `explain/fidelity.py` | Lambda + Bedrock + Guardrails |
| Final Output | Contrat JSON | `schemas/explanation.py` | DynamoDB `runs` + S3 |

Ajout par rapport au diagramme : une **fonction de gouvernance** (piste n° 2 du case). Ce n'est pas un agent de plus : ce sont des contrôles visibles répartis dans le moteur de décision (`engine/governance.py`) et le vérificateur de fidélité (`explain/fidelity.py`). Voir `08_CONFORMITE.md`.

## Qui fait quoi : LLM ou code

| Tâche | LLM | Code |
|---|:-:|:-:|
| Interpréter un profil en texte libre, proposer poids et contraintes | ✔ | validation du schéma, bornes |
| Choisir quels actifs et quelles preuves aller chercher | ✔ | outils d'accès aux données |
| Calculer rendement, volatilité, drawdown, corrélations | | ✔ |
| Argumenter pour / contre / cas de base | ✔ | chaque argument doit citer un `evidence_id` existant |
| Appliquer les contraintes, scorer, classer, rejeter | | ✔ |
| Rédiger l'explication en langage simple | ✔ | vérification chiffre par chiffre contre le registre |

Conséquence : une décision peut être rejouée et vérifiée sans relancer de modèle.

## Flux d'une analyse

1. `POST /runs` avec `profile_id`, `as_of` (date de référence) et, en option, `requested_ticker` (« Tester une idée »).
2. **Profil** → `ProfileWeights` (contraintes dures + poids, voir `03_DECISION_ENGINE.md`).
3. En parallèle :
   - **Recherche** → liste de candidats avec premières preuves qualitatives (documents, ESG, relations du graphe).
   - **Validation** → métriques déterministes pour l'univers, calculées à la date `as_of`. Comme l'univers est petit, elles sont pré-calculées pour tous les actifs, ce qui rend le parallélisme réel.
4. Jointure : `EvidencePack` par candidat = preuves qualitatives + métriques. Tout candidat sans métriques valides est écarté avec un motif.
5. **Débat** : les trois agents reçoivent le même `EvidencePack` et les mêmes contraintes.
6. **Moteur de décision** → classement, rejets motivés, désaccords conservés, ou « aucune recommandation ».
7. **Explication** → texte synthétique + liens vers les preuves ; le vérificateur de fidélité bloque toute affirmation non étayée.
8. Le mobile interroge `GET /runs/{id}` : il affiche l'étape en cours (les étapes de la machine d'états deviennent une animation de progression), puis le résultat.

## Contrats entre étapes

Tous les échanges sont des JSON validés par Pydantic (`backend/easytrade/schemas/`). Détail dans `02_AGENTS.md`.

```
Profile ─► ProfileWeights ─► CandidateList ─┐
                             MetricsTable ──┴► EvidencePack[] ─► DebateRecord[] ─► Decision ─► Explanation
```

Champs transverses, présents partout :

- `run_id`, `as_of` (date de référence de l'analyse)
- `evidence_id` pour toute donnée citée
- `claim_kind` ∈ `FAIT | HYPOTHESE | SCENARIO`

## API (première version)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/personas` | Les 3 personas du case |
| POST | `/profiles` | Créer un profil fictif |
| GET | `/profiles/{id}` | `ProfileWeights` d'un profil (persona ou fictif) — ajout P5 |
| POST | `/runs` | Lancer une analyse (asynchrone) |
| GET | `/runs/{id}` | État, étape courante, résultat |
| GET | `/runs/{id}/trace` | Trace d'exécution observable |
| GET | `/assets` | Univers d'actifs (liste de « Tester une idée ») — ajout P5 |
| GET | `/assets/{ticker}?profile_id=` | Fiche : métriques situées dans l'univers et comparées au profil, signaux |
| GET | `/assets/{ticker}/graph` | Graphe de dépendances sourcé |
| GET | `/evidence/{id}` | Une preuve : source, dates, traitement |
| GET | `/data` | Sources et contrôles qualité (écran « Données ») — ajout P5 |

Les formes exactes des réponses attendues par le mobile sont dans `mobile/src/types/contracts.ts` ; les champs proposés par le front sont listés dans `mobile/README.md`, section Contrats.

## Choix structurants

Les décisions et leurs alternatives sont consignées dans `adr/`.

- **Asynchrone.** Une analyse multi-agents prend plusieurs dizaines de secondes ; le mobile ne bloque pas et montre la progression.
- **Résultats mis en cache pour la démo.** Les exécutions des personas sont enregistrées (`run_id` stables) pour une vidéo fiable ; la démo montre aussi une exécution en direct.
- **Même code en local et sur AWS.** `orchestration/pipeline.py` enchaîne les étapes localement ; les mêmes fonctions sont appelées par les Lambda. On développe sans attendre l'infrastructure.
- **Mocks dès le premier jour.** `mobile/src/mocks/` contient un `Explanation` d'exemple conforme au contrat : le front avance en parallèle du backend.
