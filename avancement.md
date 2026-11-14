# avancement.md — EasyTrade (Datathon Polyfinances 2026, défi AlphaForge AI)

> **Mode d'emploi.** Ce fichier est la source de vérité de l'avancement. Il est mis à jour après chaque étape terminée.
> En cas d'interruption : joindre ce fichier dans une nouvelle conversation et reprendre à la **première tâche non cochée** de la section 4.
> **Règle : ne jamais recommencer une étape marquée ✅.**

Dernière mise à jour : 2026-11-14 — fin de l'étape 0

---

## 1. État des étapes

| # | Étape | État | Sortie vérifiable |
|---|---|---|---|
| 0 | Cadrage, arborescence du dépôt, documents de conception, scénarios | ✅ terminée | Dépôt `easytrade/` ; `pytest` : 5 réussis, 20 en attente |
| 1 | Socle données (P1) | ⬜ à faire | S7, S9 |
| 2 | Moteur de décision (P2) | ⬜ à faire | S4, S12 |
| 3 | Agents et explicabilité (P3) | ⬜ à faire | S1, S3, S6 en local |
| 4 | AWS (P4) | ⬜ à faire | Un run complet sur AWS |
| 5 | Mobile (P5) | ⬜ à faire | Parcours complet sur téléphone |
| 6 | Mateo / ESG + extras (P6) | ⬜ à faire | S2 |
| 7 | Livrables (P7) | ⬜ à faire | Vidéo, documentation, one-pager, README |

## 2. Fichiers créés ou modifiés

### Étape 0 (2026-11-14) — tout est créé, rien n'est modifié

Arborescence complète fichier par fichier : `docs/ARBORESCENCE.md`.

**Documents rédigés (contenu complet)**

| Fichier | Contenu |
|---|---|
| `README.md` | Présentation, démarrage, structure, données, conformité |
| `avancement.md` | Ce fichier |
| `CONTRIBUTING.md` | Règles de travail, commandes |
| `docs/00_VISION.md` | North star, question traitée, alignement sur la grille, vocabulaire |
| `docs/01_ARCHITECTURE.md` | Du diagramme aux modules, flux, contrats, API |
| `docs/02_AGENTS.md` | Fiche de chaque agent, protocole de débat, contrats JSON |
| `docs/03_DECISION_ENGINE.md` | Critères, poids par persona, contraintes, score, cohérence, sensibilité |
| `docs/04_DONNEES.md` | Jeu de départ et ses pièges, sources à ajouter, point-in-time, schémas, qualité |
| `docs/05_EXPLICABILITE.md` | Registre de preuves, trace, vérificateur de fidélité |
| `docs/06_AWS.md` | Services retenus et écartés, architecture, points à confirmer |
| `docs/07_UX_UI.md` | Parcours, écrans, graphe, composants, rédaction |
| `docs/08_CONFORMITE.md` | Règles → mécanismes → tests, registre des risques, liste de contrôle |
| `docs/09_SCENARIOS_TEST.md` | Scénarios S1 à S12 |
| `docs/10_PLAN.md` | Phases, répartition, MVP et extras, risques |
| `docs/ARBORESCENCE.md` | Arborescence complète |
| `docs/adr/README.md` + `0001` à `0005` | Décisions d'architecture |
| `docs/diagrammes/architecture_agentique.txt` | Diagramme d'origine de l'équipe |
| `backend/README.md`, `data/README.md`, `infra/README.md`, `mobile/README.md`, `notebooks/README.md` | Guides par dossier |

**Trames (structure posée, contenu à écrire)**

`docs/livrables/` : `README.md`, `script_video.md`, `documentation_technique.md`, `one_pager.md`, `pitch.md` · `backend/easytrade/agents/prompts/*.md` (6 prompts)

**Données et configuration (contenu réel)**

| Fichier | Contenu |
|---|---|
| `data/raw/starter/*` | Jeu de départ du datathon, copié sans modification (9 fichiers) |
| `data/reference/personas.json` | 3 personas de l'énoncé + poids et contraintes de départ (hypothèses) |
| `data/reference/sources_registry.csv` | 6 sources du jeu de départ renseignées, 6 sources prévues ou optionnelles |
| `data/reference/esg_evidence.csv`, `graph_edges.csv` | En-têtes seulement |
| `data/reference/forbidden_wording.txt` | Formulations refusées |
| `infra/statemachine/pipeline.asl.json` | Squelette de la machine d'états (ARN à injecter) |
| `mobile/src/mocks/*.exemple.json` | Données entièrement fictives conformes aux contrats |
| `.env.example`, `.gitignore`, `.github/workflows/ci.yml`, `backend/pyproject.toml`, `backend/requirements.txt`, `infra/cdk.json`, `infra/requirements.txt` | Configuration |

**Squelettes de code (en-tête décrivant le rôle, aucune logique)**

| Dossier | Fichiers |
|---|---:|
| `backend/easytrade/` (schemas, data, ingestion, validation, graph, agents, engine, explain, orchestration, api) | 74 `.py` |
| `backend/tests/unit/` | 8 tests en attente + `test_reference_data.py` (réel) |
| `backend/tests/scenarios/` | 12 tests en attente (S1 à S12) |
| `infra/` | 7 `.py` |
| `mobile/app/` | 14 écrans |
| `mobile/src/` | 13 composants, 4 modules API, 7 autres modules |
| `scripts/` | 4 `.py` |

## 3. Scénarios

Définitions : `docs/09_SCENARIOS_TEST.md`. Commande : `cd backend && pytest tests/scenarios -rs`.

### Scénarios d'acceptation

| ID | Scénario | État | Écart constaté |
|---|---|---|---|
| S1 | Amira : le risque élevé garde une diversification | ⏳ non exécuté | Test en attente : pipeline non implémenté |
| S2 | Mateo : l'ESG change le résultat | ⏳ non exécuté | Test en attente ; données ESG absentes |
| S3 | Robert : la demande incohérente est remise en question | ⏳ non exécuté | Test en attente : pipeline non implémenté |
| S4 | « Aucune recommandation » | ⏳ non exécuté | Test en attente : moteur non implémenté |
| S5 | Aucune fuite du futur | ⏳ non exécuté | Test en attente : filtre point-in-time non implémenté |
| S6 | Fidélité de l'explication | ⏳ non exécuté | Test en attente : vérificateur non implémenté |
| S7 | Comparabilité (devises, calendriers, ajustements) | ⏳ non exécuté | Test en attente : couche données non implémentée |
| S8 | Formulation et cadre de simulation | ⏳ non exécuté | Test en attente : filtre non implémenté |
| S9 | Exactitude et déterminisme des calculs | ⏳ non exécuté | Test en attente : métriques non implémentées |
| S10 | Graphe sourcé | ⏳ non exécuté | Test en attente ; aucune arête saisie |
| S11 | Désaccord conservé | ⏳ non exécuté | Test en attente : débat non implémenté |
| S12 | Adaptation au profil | ⏳ non exécuté | Test en attente : moteur non implémenté |

**Bilan : 0 passe, 0 échoue, 12 non exécutés.**

### Tests techniques

| Test | État | Écart |
|---|---|---|
| `unit/test_reference_data.py` (5 tests : personas, poids normalisés, contraintes bornées, registre des sources, univers de 31 actifs) | ✅ 5 / 5 | — |
| 8 autres tests unitaires | ⏳ en attente | Squelettes |
| Validité de tous les fichiers JSON et Python du dépôt | ✅ | — |

## 4. Tâches restantes, dans l'ordre

Cocher au fur et à mesure. Les blocs A et F peuvent avancer en parallèle des autres.

### A. Décisions et confirmations (bloquantes pour certaines tâches)

- [ ] A1. Confirmer dates limites, plateforme de dépôt et formats (consignes logistiques officielles).
- [ ] A2. Confirmer le compte AWS : services autorisés, région, modèles Bedrock ouverts, budget. Bloque E.
- [ ] A3. Trancher le nom et le sous-titre (ADR 0005) et le vocabulaire « pistes à explorer ».
- [ ] A4. Trancher Alpaca / Finnhub après lecture de leurs conditions (ADR 0002).
- [ ] A5. Répartir les rôles (`docs/10_PLAN.md`) ; dépôt public ou privé.

### B. Socle données — P1

- [ ] B1. `schemas/evidence.py`, `explain/evidence_ledger.py` : modèle et registre de preuves.
- [ ] B2. `data/loaders.py`, `ingestion/starter_kit.py` : charger le jeu de départ, tables préparées.
- [ ] B3. `data/calendar.py`, `data/fx.py` : calendriers, conversion CAD. → `test_fx_calendar`
- [ ] B4. `data/point_in_time.py` : filtre `published_at ≤ as_of`, délais macro. → `test_point_in_time`, **S5**
- [ ] B5. `validation/metrics.py`, `validation/risk.py` : indicateurs + preuves. → `test_metrics`, **S9**
- [ ] B6. `validation/data_quality.py` : rapport de qualité ; traiter l'anomalie CNQ.TO.
- [ ] B7. Scénario **S7** au vert.

### C. Moteur de décision — P2

- [ ] C1. `schemas/` restants (profile, weights, candidate, metrics, debate, decision, explanation, trace).
- [ ] C2. `engine/constraints.py`. → `test_constraints`
- [ ] C3. `engine/scoring.py` avec contributions. → `test_scoring`
- [ ] C4. `engine/decision.py` + « aucune recommandation ». → **S4**
- [ ] C5. `engine/coherence.py` (« Tester une idée »).
- [ ] C6. `orchestration/pipeline.py` sans LLM (débat simulé) ; `scripts/run_local.py`. → **S12**
- [ ] C7. Calibrer poids et contraintes de `personas.json` sur les résultats.

### D. Agents et explicabilité — P3

- [ ] D1. `agents/llm_client.py` : Bedrock, sortie structurée, faux client de test.
- [ ] D2. `agents/profile_weighting.py` + prompt.
- [ ] D3. `agents/tools.py`, `agents/research.py` + prompt.
- [ ] D4. `agents/debate/*` : tours 1 et 3 + prompts. → **S11**
- [ ] D5. `agents/explanation.py`, `explain/fidelity.py`, `explain/wording.py`. → `test_fidelity`, `test_wording`, **S6**, **S8**
- [ ] D6. `explain/trace.py`, `engine/governance.py`.
- [ ] D7. Scénarios **S1** et **S3** au vert en local ; enregistrer les runs des personas.

### E. AWS — P4 (dès que A2 est levé)

- [ ] E1. `DataStack` : S3, DynamoDB ; `scripts/seed_aws.py`.
- [ ] E2. `PipelineStack` : Lambda par étape, machine d'états, droits Bedrock.
- [ ] E3. `ApiStack` : API Gateway + `api/app.py` et routes.
- [ ] E4. Un run complet sur AWS ; trace visible ; captures pour la vidéo.
- [ ] E5. IAM à privilège minimal, secrets, étiquettes de coût.

### F. Mobile — P5 (démarre tout de suite avec les données fictives)

- [ ] F1. Initialiser le projet Expo (`mobile/README.md`) ; thème ; `SimulationBanner`.
- [ ] F2. `src/types/contracts.ts`, `src/api/*` avec bascule données fictives / API.
- [ ] F3. Profil : personas, questionnaire, résumé.
- [ ] F4. Pistes à explorer : `MoveCard`, `FitBadge`, `RunProgress`, écartées, « aucune recommandation ».
- [ ] F5. Fiche d'une piste : risque, débat, contributions, « ce que nous ne savons pas ».
- [ ] F6. « Pourquoi ? » : `EvidenceChip`, écran preuve, parcours de l'analyse.
- [ ] F7. Tester une idée.
- [ ] F8. Graphe de dépendances, version radiale.
- [ ] F9. Brancher l'API réelle.

### G. Graphe et ESG — P1 / P6

- [ ] G1. Saisir les arêtes sourcées de 5 à 8 sociétés dans `graph_edges.csv` ; `graph/*`. → `test_graph_edges`, **S10**
- [ ] G2. Saisir les preuves ESG dans `esg_evidence.csv` ; `ingestion/esg.py`. → **S2**
- [ ] G3. `ingestion/edgar.py` : fondamentaux pour le critère `qualite`.

### H. Extras (seulement si S1, S3, S5, S6 passent ; ordre de `docs/10_PLAN.md`)

- [ ] H1. Comparaison de deux profils. · H2. Sensibilité. · H3. Guardrails. · H4. Tour 2 du débat. · H5. Version web hébergée. · H6. Graphe animé. · H7. Jauge de sentiment. · H8. Knowledge Bases, Athena.

### I. Livrables — P7

- [ ] I1. Script et tournage de la vidéo (deux personas contrastés).
- [ ] I2. Documentation technique avec l'exemple d'explicabilité tiré d'un run réel.
- [ ] I3. One-pager.
- [ ] I4. README final (dépendances, sources, configuration, démarrage).
- [ ] I5. Liste de contrôle de `docs/08_CONFORMITE.md` ; répétition du pitch.

## 5. Hypothèses prises à l'étape 0 (à valider par l'équipe)

1. Reformulation « best moves » → « pistes à explorer » pour rester hors du conseil personnalisé.
2. Jeu de départ comme socle ; Alpaca et Finnhub optionnels et désactivés ; suivi de wallets et opinions d'experts non retenus.
3. Ajout de « Tester une idée » (répond au test Robert) et d'une fonction de gouvernance visible.
4. Poids et contraintes par persona : valeurs de départ, à calibrer.
5. Step Functions + Lambda + Bedrock ; CDK en Python ; Expo pour le mobile.
6. « Prochains accords potentiels » du graphe : hors MVP, sinon étiquetés hypothèse.
