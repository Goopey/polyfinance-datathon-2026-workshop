# avancement.md — EasyTrade (Datathon Polyfinances 2026, défi AlphaForge AI)

> **Mode d'emploi.** Ce fichier est la source de vérité de l'avancement. Il est mis à jour après chaque étape terminée.
> En cas d'interruption : joindre ce fichier dans une nouvelle conversation et reprendre à la **première tâche non cochée** de la section 4.
> **Règle : ne jamais recommencer une étape marquée ✅.**

Dernière mise à jour : 2026-11-14 — étape 2 (P2) en cours : contraintes, scoring, décision, cohérence ; S4 et S12 au vert (restent C6 pipeline et C7 calibrage). Étape 5 (P5) réalisée sur données fictives (F1 à F8) ; F9, branchement de l'API réelle, en attente de P3 et P4

---

## 1. État des étapes

| # | Étape | État | Sortie vérifiable |
|---|---|---|---|
| 0 | Cadrage, arborescence du dépôt, documents de conception, scénarios | ✅ terminée | Dépôt `easytrade/` ; `pytest` : 5 réussis, 20 en attente |
| 1 | Socle données (P1) | ✅ terminée | S5, S7, S9 verts ; `pytest` : 42 réussis, 14 en attente (P2 et suivantes) |
| 2 | Moteur de décision (P2) | 🟦 en cours | S4, S12 verts ; restent C6 (pipeline sans LLM) et C7 (calibrage) |
| 3 | Agents et explicabilité (P3) | ⬜ à faire | S1, S3, S6 en local |
| 4 | AWS (P4) | ⬜ à faire | Un run complet sur AWS |
| 5 | Mobile (P5) | 🟨 partielle : F1 à F8 ✅ sur données fictives ; F9 (API réelle) bloquée par P2 à P4 | Parcours complet vérifié de bout en bout (export web, clics réels) ; reste : téléphone + API réelle |
| 6 | Mateo / ESG + extras (P6) | ⬜ à faire | S2 |
| 7 | Livrables (P7) | ⬜ à faire | Vidéo, documentation, one-pager, README |

## 2. Fichiers créés ou modifiés

### Étape 5 — P5 Mobile (2026-11-14), sur données fictives

Fait en parallèle de P2, comme prévu par `docs/10_PLAN.md` (« P5 avec données simulées démarre en parallèle »). Détail : `mobile/README.md`. Aucun fichier `backend/` modifié.

**Projet Expo (créé)** : `mobile/package.json`, `package-lock.json`, `app.json`, `tsconfig.json`, `metro.config.js` (import de `data/reference/personas.json`), `assets/*.png` (icônes du gabarit Expo). Expo SDK 58, `expo-router`, TanStack Query, Zustand + AsyncStorage, `react-native-svg`, `react-native-gesture-handler`.

| Fichiers | Contenu |
|---|---|
| `src/types/contracts.ts` | Miroir TS des contrats de réponse de l'API ; `Evidence` identique à `schemas/evidence.py` ; champs proposés listés dans `mobile/README.md` |
| `src/api/*` | Bascule `EXPO_PUBLIC_USE_MOCKS` ; routes de `01_ARCHITECTURE.md` + `GET /profiles/{id}`, `GET /assets`, `GET /data` |
| `src/mocks/fixtures.ts`, `server.ts` | Univers fictif de 8 actifs, registre de preuves fictif, serveur fictif reproduisant la forme du moteur (contraintes, score, concentration, aucune recommandation, cohérence) |
| `src/mocks/*.exemple.json` | Régénérés depuis le serveur fictif : exemples conformes aux contrats de réponse |
| `src/components/*` (12 composants + `ui.tsx`) | Tous ceux de `07_UX_UI.md` sauf `SentimentGauge` (extra n° 8, squelette conservé) |
| `src/store/*`, `src/hooks/useBaseRun.ts`, `src/theme/*`, `src/i18n/*`, `src/format.ts` | État persisté, lancement / reprise d'un run, thème, textes, glossaire, formats français |
| `app/*` (14 écrans) | Tous les écrans de `07_UX_UI.md`, y compris Comparer (extra n° 2, réalisé côté interface) et Données |

**Documentation modifiée** : `mobile/README.md` (réécrit), `docs/01_ARCHITECTURE.md` (table d'API : 3 routes ajoutées), `docs/ARBORESCENCE.md`, ce fichier.

**Vérifications** : `tsc --noEmit` sans erreur ; `npx expo-doctor` 20/20 ; export web réussi ; parcours de bout en bout dans Chrome sans tête, avec clics réels (persona Robert → pistes → écartées → fiche → débat → preuve → parcours de l'analyse → Tester une idée `ACTIF_G` « Incohérent » → mode Avancé → questionnaire → « Aucune piste ») : 14 étapes sur 14, aucune erreur console. Sorties fictives des 3 personas et de « Tester une idée » : 0 terme de `forbidden_wording.txt`, toutes les preuves citées existent, aucune publiée après `as_of`.

**Non vérifié** : affichage sur un vrai téléphone (Expo Go) ; branchement à l'API réelle (inexistante).

**Écarts avec les schémas P2** (à résoudre en F9, de préférence dans la couche API / `Explanation`, qui produit le contrat de présentation) : `ProfileWeights` (`persona_id`/`constraints`/`rationale: str` contre `profile_id`/`hard_constraints`/liste) ; `Confidence` au masculin (`élevé`, `moyen`) contre le féminin de `docs/02_AGENTS.md` et du mobile (`élevée`, `moyenne`) ; `Rejection.rule` contre `RejectedItem.kind` ; `ScoredCandidate.criteria[]` contre `contributions` ; `CoherenceReport` (`Tension{dimension, detail, severe, evidence_id}`, `context: str`, `alternatives: tickers`) contre des `Claim` sourcés et des alternatives justifiées.

### Étape 2 — P2 Moteur de décision (2026-11-14)

**Schémas (squelettes remplacés par des contrats Pydantic — C1)**

| Fichier | Contenu |
|---|---|
| `schemas/weights.py` | `CRITERIA`, `HardConstraints` (bornes validées), `ProfileWeights` (somme des poids = 1, `from_persona`) |
| `schemas/profile.py` | `Profile`, `HorizonYears`, `from_persona` |
| `schemas/candidate.py` | `Asset`, `CriterionScore`, `ScoredCandidate` (contributions conservées), `Rejection` |
| `schemas/decision.py` | `Decision` (classement, rejets, « aucune recommandation », confiance) |
| `schemas/coherence.py` | `CoherenceReport`, `Tension`, `Verdict` |
| `schemas/__init__.py` | Point d'import unique des contrats stables |

**Moteur (déterministe, sans LLM)**

| Fichier | Contenu |
|---|---|
| `engine/signals.py` | Signaux orientés par critère depuis la table d'indicateurs ; diversification = proxy de rareté sectorielle (à remplacer par la corrélation, bloc G) ; esg/qualite/preferences manquants |
| `engine/constraints.py` | `screen_assets` : admissibles / rejetés motivés (crypto, spéculatif, exclusion ESG) ; `basket_caps` (garde-fous de panier) — C2 |
| `engine/scoring.py` | `percentile_rank`, `score_candidates` : rang centile, contributions, critères manquants, classement déterministe — C3 |
| `engine/decision.py` | `decide` : assemblage, « aucune recommandation » (3 cas), confiance selon la couverture — C4 |
| `engine/coherence.py` | `evaluate_idea` (« Tester une idée ») : tensions chiffrées, verdict, alternatives — C5 |

**Tests (squelettes remplacés par des tests réels)**

`unit/test_constraints.py` (4), `unit/test_scoring.py` (6), `scenarios/test_s04` (2), `scenarios/test_s12` (3, sur les vraies données P1). Bilan `pytest` : 57 réussis, 10 en attente (D et G).

**Reste de P2** : C6 `orchestration/pipeline.py` sans LLM (débat simulé) + `scripts/run_local.py` ; C7 calibrage des poids/contraintes de `personas.json`. S12 est déjà vert au niveau du moteur (`decide` par persona).

### Étape 1 — P1 Socle données (2026-11-14)

**Code (squelettes remplacés par des implémentations)**

| Fichier | Contenu |
|---|---|
| `backend/easytrade/config.py` | Chemins, `as_of`, délais de publication macro, seuils qualité (hypothèses) |
| `backend/easytrade/schemas/evidence.py`, `schemas/metrics.py` | Modèles `Evidence`, `EvidenceDraft`, `MetricResult` |
| `backend/easytrade/explain/evidence_ledger.py` | Registre de preuves : identifiants `EV-nnnnnn`, déduplication, refus des preuves futures |
| `backend/easytrade/data/loaders.py` | Lecture typée du jeu de départ, trois dates par enregistrement |
| `backend/easytrade/data/sources_registry.py` | Lecture de `sources_registry.csv` ; refus d'une source non « utilisé » |
| `backend/easytrade/data/calendar.py`, `data/fx.py` | Calendriers, annualisation 252/365, alignement ; conversion CAD, report du dernier taux |
| `backend/easytrade/data/point_in_time.py` | `PointInTimeStore`, `filter_published`, délais macro |
| `backend/easytrade/validation/metrics.py`, `validation/risk.py` | Indicateurs, corrélations, une preuve par valeur |
| `backend/easytrade/validation/data_quality.py` | 8 contrôles, anomalie CNQ.TO, `quality_report.json` |
| `backend/easytrade/ingestion/starter_kit.py`, `scripts/bootstrap_data.py` | Tables préparées dans `data/curated/` (Parquet, `evidence.jsonl`, rapport) |

**Tests**

Réels : `unit/test_fx_calendar.py`, `test_point_in_time.py`, `test_metrics.py`, et nouveaux `test_evidence_ledger.py`, `test_data_quality.py` ; `scenarios/test_s05`, `test_s07`, `test_s09`. Fixtures `settings`, `store`, `registry` ajoutées à `tests/conftest.py`.

**Documentation modifiée**

`docs/04_DONNEES.md` (section 9, hypothèses de la couche données), `backend/README.md` (version de Python, commande `bootstrap_data.py`), ce fichier.

**Environnement**

Python système 3.9 (< 3.11 exigé) : `backend/.venv` créé avec `uv` (Python 3.12), ignoré par git. Aucune source nouvelle : `sources_registry.csv` inchangé. Rien n'est commité.

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
| `.env.example`, `.gitignore`, `backend/pyproject.toml`, `backend/requirements.txt`, `infra/cdk.json`, `infra/requirements.txt` | Configuration |

**Squelettes de code (en-tête décrivant le rôle, aucune logique)** — état à la fin de l'étape 0 ; les modules de P1 listés plus haut ont depuis été implémentés.

| Dossier | Fichiers |
|---|---:|
| `backend/easytrade/` (schemas, data, ingestion, validation, graph, agents, engine, explain, orchestration, api) | 74 `.py` |
| `backend/tests/unit/` | Tests réels pour P1 et `test_reference_data.py` ; 5 squelettes restants (P2 et suivantes) |
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
| S4 | « Aucune recommandation » | ✅ passe | `test_s04` : univers crypto-only exclu (Mateo) → aucun admissible ; et signaux manquants → preuves insuffisantes |
| S5 | Aucune fuite du futur | ✅ passe | `test_s05_aucune_fuite_du_futur.py` ; analyse à 2023-06-30 identique sur un jeu amputé du futur |
| S6 | Fidélité de l'explication | ⏳ non exécuté | Test en attente : vérificateur non implémenté |
| S7 | Comparabilité (devises, calendriers, ajustements) | ✅ passe | 4 tests : CAD et dernier taux connu, adj_close, 7 fractionnements non réappliqués, 252 contre 365 |
| S8 | Formulation et cadre de simulation | ⏳ non exécuté | Test en attente : filtre non implémenté |
| S9 | Exactitude et déterminisme des calculs | ✅ passe | Exécutions identiques ; XIU.TO, AAPL, BTC-USD recoupés par calcul sans pandas (tolérance relative 1e-9) |
| S10 | Graphe sourcé | ⏳ non exécuté | Test en attente ; aucune arête saisie |
| S11 | Désaccord conservé | ⏳ non exécuté | Test en attente : débat non implémenté |
| S12 | Adaptation au profil | ✅ passe | `test_s12` : même univers (8 actifs réels), classements différents pour Amira et Robert, contributions alignées sur les poids, déterministe |

**Bilan : 5 passent (S4, S5, S7, S9, S12), 0 échoue, 7 non exécutés.**

### Tests techniques

| Test | État | Écart |
|---|---|---|
| `unit/test_reference_data.py` (5 tests : personas, poids normalisés, contraintes bornées, registre des sources, univers de 31 actifs) | ✅ 5 / 5 | — |
| Tests unitaires P1 : `test_fx_calendar`, `test_point_in_time`, `test_metrics`, `test_evidence_ledger`, `test_data_quality` | ✅ | — |
| Tests unitaires P2 : `test_constraints` (4), `test_scoring` (6) | ✅ | — |
| 3 autres tests unitaires (D et G) : `test_fidelity`, `test_wording`, `test_graph_edges` | ⏳ en attente | Squelettes |
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

- [x] B1. `schemas/evidence.py`, `explain/evidence_ledger.py` : modèle et registre de preuves.
- [x] B2. `data/loaders.py`, `ingestion/starter_kit.py` : charger le jeu de départ, tables préparées.
- [x] B3. `data/calendar.py`, `data/fx.py` : calendriers, conversion CAD. → `test_fx_calendar`
- [x] B4. `data/point_in_time.py` : filtre `published_at ≤ as_of`, délais macro. → `test_point_in_time`, **S5**
- [x] B5. `validation/metrics.py`, `validation/risk.py` : indicateurs + preuves. → `test_metrics`, **S9**
- [x] B6. `validation/data_quality.py` : rapport de qualité ; traiter l'anomalie CNQ.TO.
- [x] B7. Scénario **S7** au vert.

### C. Moteur de décision — P2

- [x] C1. `schemas/` du moteur (profile, weights, candidate, decision, coherence ; metrics/evidence faits en P1). `debate`, `explanation`, `trace` restent à P3 (bloc D).
- [x] C2. `engine/constraints.py` + `engine/signals.py`. → `test_constraints`
- [x] C3. `engine/scoring.py` avec contributions. → `test_scoring`
- [x] C4. `engine/decision.py` + « aucune recommandation ». → **S4**
- [x] C5. `engine/coherence.py` (« Tester une idée »).
- [ ] C6. `orchestration/pipeline.py` sans LLM (débat simulé) ; `scripts/run_local.py`. **S12 déjà vert au niveau du moteur**, reste le câblage pipeline + CLI.
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

- [x] F1. Initialiser le projet Expo (`mobile/README.md`) ; thème ; `SimulationBanner`.
- [x] F2. `src/types/contracts.ts`, `src/api/*` avec bascule données fictives / API.
- [x] F3. Profil : personas, questionnaire, résumé.
- [x] F4. Pistes à explorer : `MoveCard`, `FitBadge`, `RunProgress`, écartées, « aucune recommandation ».
- [x] F5. Fiche d'une piste : risque, débat, contributions, « ce que nous ne savons pas ».
- [x] F6. « Pourquoi ? » : `EvidenceChip`, écran preuve, parcours de l'analyse.
- [x] F7. Tester une idée.
- [x] F8. Graphe de dépendances, version radiale.
- [ ] F9. Brancher l'API réelle. Côté mobile, le client HTTP est prêt (`EXPO_PUBLIC_USE_MOCKS=false`). Bloqué par C (schémas Pydantic alignés sur `contracts.ts`), E3 (routes). Puis : test sur téléphone avec Expo Go.
- [ ] F10. Remplacer les données fictives de la vidéo par des runs réels (aucun chiffre fictif à l'écran).

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

## 6. Hypothèses prises à l'étape 1 (à valider par l'équipe)

Détail et valeurs : `docs/04_DONNEES.md` section 9, `backend/easytrade/config.py`.

1. Délais de publication macro prudents : IPC américain 1 mois + 15 j, chômage 1 mois + 7 j, IPC canadien 1 mois + 25 j ; série inconnue refusée.
2. Seuils qualité : trou > 5 séances, variation > 25 % en un jour, minimum 252 observations, fractionnement suspect si ratio < 1,5.
3. Indicateurs en CAD ; annualisation 252 (actions, FNB) et 365 (crypto) ; fenêtres : toute la période, 3 ans, 1 an, plus 2022 et pires périodes glissantes de 1 et 3 ans.
4. Corrélation sur les dates communes, sans remplissage ; week-ends crypto : dernier taux de change connu.
5. CNQ.TO : « fractionnement » 1,021 non appliqué, signalé dans les limites de chaque preuve ; vérification auprès des relations investisseurs toujours à faire.
6. S5 rattaché à P1 (bloc B4 de ce fichier), bien que `docs/10_PLAN.md` ne liste que S7 et S9 pour cette phase.
7. Concentration sectorielle : renvoyée à P2 (dépend d'un portefeuille).
8. Le test S9 relit les CSV avec `csv`/`statistics` (sans pandas) pour le calcul indépendant : seule exception aux accès via `easytrade/data/`, limitée aux tests.
9. Décision de l'équipe : pas d'intégration continue (CI) pour le moment. Aucun `.github/workflows/` ; les tests se lancent à la main (`cd backend && pytest`). Références à `ci.yml` retirées de `avancement.md` et de `docs/ARBORESCENCE.md`.

## 7. Hypothèses prises à l'étape 5 (à valider par l'équipe)

1. Données fictives par défaut (`EXPO_PUBLIC_USE_MOCKS=true`), signalées par un second bandeau ; aucun chiffre fictif dans la vidéo.
2. Champs de réponse proposés par le front (`mobile/README.md`, section Contrats) et 3 routes ajoutées : `GET /profiles/{id}`, `GET /assets`, `GET /data`.
3. Seuils indicatifs de risque par tolérance, affichés comme `HYPOTHESE` sur la fiche et dans « Tester une idée » : volatilité 18 / 25 / 45 %, perte maximale −20 / −30 / −50 % (faible / modérée / élevée). Valeurs du serveur fictif seulement ; à fixer dans le moteur (C7).
4. Effet sur le panier simulé : moyenne pondérée des volatilités sans corrélations (approximation signalée dans la preuve `SCENARIO`) ; à remplacer par le calcul du moteur.
5. Graphe : version radiale fixe, profondeur 1 ; la liste des relations sous le graphe donne le même contenu (accessibilité).
6. Poids modifiables sur l'écran de résumé par pas de 5 points, renormalisés ; la modification crée un nouveau profil (`POST /profiles` avec `base_persona` et `weights_override`).
7. Questionnaire : 3 gabarits (faible → Robert, modérée → Mateo, élevée → Amira) ajustés par les préférences et exclusions ; à reprendre par l'agent de pondération (D2).
