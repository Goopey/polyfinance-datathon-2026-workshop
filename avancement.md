# avancement.md — EasyTrade (Datathon Polyfinances 2026, défi AlphaForge AI)

> **Mode d'emploi.** Ce fichier est la source de vérité de l'avancement. Il est mis à jour après chaque étape terminée.
> En cas d'interruption : joindre ce fichier dans une nouvelle conversation et reprendre à la **première tâche non cochée** de la section 4.
> **Règle : ne jamais recommencer une étape marquée ✅.**

Dernière mise à jour : 2026-11-15 — étape 4 (P4) **déployée** sur le compte d'atelier (us-east-1) : 3 piles CDK, API en ligne, premières analyses réelles sur AWS terminées (amira, mateo, robert ; ~2 min chacune ; vérificateur de fidélité passé) ; coût mesuré ≈ 0,35 $ par analyse ; précalcul : 3 / 96. Avant, le 2026-11-14 : code AWS prêt à déployer (CDK, 8 Lambda, Step Functions, API sur DynamoDB / S3), résultat identique au local vérifié par `tests/aws` ; client Bedrock corrigé pour les modèles Claude actuels ; restent le déploiement et le premier run sur le compte d'atelier (E4, D8). Avant : étape 3 (P3) terminée en local : agents, débat, explication, vérificateur de fidélité, pipeline complet (`scripts/run_local.py`) ; S1, S3, S6, S11 au vert, S8 partiel. Les agents tournent en mode **simulé** (règles Python, aucun modèle) : le client Bedrock est écrit mais n'a pas été exécuté contre AWS (A2 non levé). C6 fait avec P3 ; C7 (calibrage) reste ouvert. Étape 5 (P5) : F9 fait, l'application est branchée sur l'API réelle en local (`backend/easytrade/api/`), contrat vérifié par des tests des deux côtés et par un parcours complet dans un navigateur ; restent l'essai sur téléphone et le déploiement (P4)

---

## 1. État des étapes

| # | Étape | État | Sortie vérifiable |
|---|---|---|---|
| 0 | Cadrage, arborescence du dépôt, documents de conception, scénarios | ✅ terminée | Dépôt `easytrade/` ; `pytest` : 5 réussis, 20 en attente |
| 1 | Socle données (P1) | ✅ terminée | S5, S7, S9 verts ; `pytest` : 42 réussis, 14 en attente (P2 et suivantes) |
| 2 | Moteur de décision (P2) | 🟦 en cours | S4, S12 verts ; C6 fait avec P3 ; reste C7 (calibrage) |
| 3 | Agents et explicabilité (P3) | ✅ terminée en local (agents simulés) ; exécution sur Bedrock à faire dès A2 | S1, S3, S6, S11 verts ; `pytest` : 195 réussis, 4 en attente |
| 4 | AWS (P4) | 🟨 déployé : E1 à E5 ✅ ; E6 (précalcul) 3 / 96 ; D8 (rejouer S1, S3, S6 sur Bedrock) en cours | `cdk synth` réussi (3 piles) ; `tests/aws` : machine d'états = pipeline local ; `pytest` : 261 réussis, 3 en attente |
| 5 | Mobile (P5) | 🟨 F1 à F9 ✅ : application branchée sur l'API réelle en local ; restent l'essai sur téléphone et l'API déployée (P4) | `npm run e2e:api` : parcours complet sur l'API réelle, 14 étapes, aucune erreur ; `pytest` : 247 réussis, 3 en attente ; `npm test` : 20 réussis |
| 6 | Mateo / ESG + extras (P6) | ⬜ à faire | S2 |
| 7 | Livrables (P7) | ⬜ à faire | Vidéo, documentation, one-pager, README |

## 2. Fichiers créés ou modifiés

### Étape 4 — P4 AWS (2026-11-14), code prêt, non déployé

Commandes de déploiement : `infra/README.md`. Conception : `docs/06_AWS.md` (section « Réalisation (P4) »).

| Fichier | Contenu |
|---|---|
| `orchestration/pipeline.py` | `run_pipeline` découpé en `RunContext` + fonctions d'étape (`stage_profile` … `stage_explanation`, `debate_one`, `record_debate`) ; comportement local inchangé (les 247 tests d'avant restent verts) |
| `orchestration/aws_runtime.py` (nouveau) | Données copiées de S3 au démarrage à froid ; contexte des runs (`S3StateStore` / `LocalStateStore`) ; table (`DynamoRunTable` / `LocalRunTable`) |
| `orchestration/handlers/*` | Une Lambda par état + `common.py` (règle d'erreur : relance si Bedrock indisponible, sinon échec visible) + `failure.py` |
| `api/aws_service.py` (nouveau), `api/deps.py`, `api/service.py` | `AwsApiService` choisi par `EASYTRADE_ENV=aws` ; `_prepare_run` extrait |
| `agents/llm_client.py` | Bedrock : sans `temperature` ni `toolChoice` forcé, `max_tokens` 16 000, blocs de raisonnement ignorés |
| `explain/trace.py` | `set_on_step` |
| `infra/app.py`, `infra/stacks/{data,pipeline,api}_stack.py`, `infra/build_lambda.py`, `infra/statemachine/pipeline.asl.json`, `infra/cdk.json`, `infra/requirements.txt` | CDK (us-east-1), paquets Lambda sans Docker (93,8 Mo), machine d'états |
| `scripts/seed_aws.py` | Recopie de `data/` vers S3 sans redéployer |
| `backend/tests/aws/` (nouveau) | Interpréteur de la machine d'états ; 12 tests : résultat identique au local (amira, robert + TSLA, mateo), artefacts, relances puis échec visible, échec sans relance, API sur deux « conteneurs », profil fictif, lanceur |
| `scripts/precompute.py` (nouveau), `api/aws_service.py` (vues de profil dans la table), `pipeline.py` (`candidate_workers`), `scripts/run_local.py` (progression, `--max-candidates`), `llm_client.py` (délai de lecture 300 s) | Objectif « moins de 5 s » : moteur seul 0,3 s mesuré, agents en direct 1,5 à 2 min ⇒ agents précalculés (`docs/06_AWS.md`, section « Précalcul ») ; 4 tests |

**Non vérifié** : aucune exécution sur AWS (pas d'identifiants) ; import du paquet sur Linux / Python 3.12 (construit pour, non exécuté) ; quotas Bedrock du compte d'atelier.


### Branchement mobile ↔ backend — F9 et routes de E3 en local (2026-11-14)

Constat de départ : le pipeline (P3) produisait déjà `Explanation` et `RunTrace` au format du mobile, mais `api/*` était un squelette, `ProfileWeights` avait une autre forme, et aucune route ne servait la fiche, le graphe, les preuves ni les données. Détail : `docs/01_ARCHITECTURE.md` (API), `mobile/README.md`.

**Backend**

| Fichier | Contenu |
|---|---|
| `schemas/api.py` (nouveau) | Contrats de réponse, miroir de `contracts.ts` : `ProfileWeightsView`, `ProfileDraft`, `RunRequest`, `RunStatusView`, `AssetSheet`, `DependencyGraph`, `DataOverview` |
| `api/service.py` (nouveau) | `ApiService` : lance le pipeline dans un fil d'exécution, garde runs et profils fictifs en mémoire, traduit les schémas internes vers les contrats du mobile ; preuves, fiches et graphe lus dans le registre du run |
| `api/app.py`, `api/deps.py`, `api/routes_*.py` | Application FastAPI, 12 routes, CORS, 404 / 422 ; service créé à la première requête |
| `orchestration/pipeline.py` | Ajouts sans changement de comportement : `on_step` (progression), `profile_source`, `RunResult.metrics` |
| `explain/trace.py`, `data/sources_registry.py` | `TraceRecorder(on_step=…)` ; `SourcesRegistry.records()` |
| `requirements.txt` | + `httpx`, `jsonschema` (tests de l'API) |

**Mobile**

| Fichier | Contenu |
|---|---|
| `src/api/assets.ts`, `app/preuve/[id].tsx`, `app/piste/[ticker].tsx`, `app/donnees.tsx` | `run_id` transmis pour la preuve, la fiche, le graphe et les données |
| `src/types/contracts.ts` | + `hard_constraints.speculatif`, `ProfileDraft.base_persona`, `TraceStep.attempts / inputs / evidence_in` |
| `app/run/[id].tsx`, `src/mocks/server.ts` | Noms d'étapes du pipeline réel (`dossiers_de_preuves`, `debate.bull.round1`, `controle.plafonds_panier`…) ; étape « sans objet » ; notes affichées |
| `app/onboarding/questionnaire.tsx`, `resume.tsx` | Exclusions limitées à celles que le moteur applique (crypto, spéculatif, controverses) ; règle « spéculatif » affichée |
| `src/components/RiskMeter.tsx`, `SupplyChainGraph.tsx`, `src/format.ts`, `src/i18n/fr.ts`, `app/(tabs)/_layout.tsx` | Rendement 2022, étiquette Hypothèse sur une arête sourcée, décomptes sans décimales, `etf_commodity`, hauteur de la barre d'onglets |
| `contracts.schema.json`, `scripts/contracts-schema.mjs` (nouveaux) | Schéma JSON du contrat, généré depuis `contracts.ts` (`npm run contracts`) |
| `tests/contracts.test.ts`, `tests/client.test.ts`, `e2e/run.mjs` (nouveaux) | Voir ci-dessous |

**Données de référence** : `sources_registry.csv` + 1 ligne (`profil_questionnaire`), source des phrases d'un profil composé par questionnaire.

**Tests mis en place**

| Commande | Ce qui est vérifié |
|---|---|
| `cd backend && pytest tests/api` (51 tests) | Chaque route de l'API réelle contre `mobile/contracts.schema.json` ; résultat identique à celui du pipeline local ; chiffre d'une fiche = valeur de sa preuve ; preuves propres à un run ; aucune preuve après `as_of` ; refus 404 / 422 ; liste exacte des routes |
| `cd backend && pytest tests/scenarios/test_s08*` | S8 point 3 : aucune route d'ordre, deux écritures seulement, corps sans champ de transaction |
| `cd mobile && npm test` (20 tests) | Schéma à jour par rapport à `contracts.ts` ; serveur fictif conforme au même schéma ; URL et `run_id` envoyés par le client ; erreurs 404 ; formulations refusées ; preuves citées existantes |
| `cd mobile && npm run e2e:api` | Navigateur réel sur l'API réelle : Robert → pistes → fiche → preuve → parcours de l'analyse → Tester une idée (Tesla, « incohérent ») → Données → Comparer → questionnaire → profil fictif analysé → Mateo « aucune recommandation ». Échoue sur toute erreur de console ou réponse HTTP en erreur |
| `cd mobile && npm run e2e:mock` | Même parcours sur les données fictives |

Deux garde-fous vérifient que le validateur refuse bien un champ en trop, un champ manquant et une valeur hors énumération (dont `élevé` au lieu de `élevée`).

**Résultats (2026-11-14)** : `pytest` 247 réussis, 3 en attente (S2, S10, `test_graph_edges`) ; `npm test` 20 réussis ; `npm run typecheck` sans erreur ; `expo-doctor` 20/20 ; `e2e:api` et `e2e:mock` réussis. Un défaut trouvé par les tests et corrigé : après une étape en échec, l'étape suivante s'affichait aussi « échec » au lieu de « en attente ».

**Non fait ou non vérifié**

- Essai sur un vrai téléphone (Expo Go) ; API déployée sur AWS (P4) : runs et profils fictifs sont en mémoire du processus, perdus au redémarrage (le mobile relance alors l'analyse ; un profil fictif est à recréer).
- Graphe : `graph_edges.csv` est vide et ses sources (`sec_edgar`, `sedar_plus`) sont au statut « prévu » ; l'API ne sert donc aucune arête pour l'instant (bloc G). La traduction des arêtes est testée sur des arêtes simulées.
- `backend/.venv` créé sur ce poste avec `python -m venv --system-site-packages` pour installer `fastapi` et `uvicorn` sans toucher à Anaconda (ignoré par git).

### Étape 3 — P3 Agents et explicabilité (2026-11-14), en local

Commande : `python scripts/run_local.py --persona robert --ticker TSLA -v` (depuis la racine). Détail de conception : `docs/02_AGENTS.md` (section « Réalisation »), `docs/03_DECISION_ENGINE.md` (section « Hypothèses ajoutées à l'étape P3 »), `docs/05_EXPLICABILITE.md` (section 4).

**Schémas (squelettes remplacés, ou champs ajoutés sans casser P2)**

| Fichier | Contenu |
|---|---|
| `schemas/debate.py` | `Claim`, `DebateTurnDraft` (sortie du modèle), `DebateTurn`, `DebateRecord` (dissidence) |
| `schemas/explanation.py` | `Explanation`, `ExplanationItem`, `RejectedItem`, `CoherenceAnalysis` : miroir de `mobile/src/types/contracts.ts` |
| `schemas/trace.py` | `TraceStep`, `RunTrace` |
| `schemas/candidate.py` | + `Candidate`, `CandidateList`, `EvidencePack` |
| `schemas/decision.py` | + `retained`, `displaced`, `candidate_confidence`, `to_review` |
| `schemas/coherence.py`, `schemas/weights.py` | + `Tension.evidence_ids` ; + `CRITERION_LABELS` |

**Agents**

| Fichier | Contenu |
|---|---|
| `agents/llm_client.py` | `structured_call` (schéma, une relance, `LLMOutputError`), `BedrockClient` (API Converse, sortie par outil forcé, Guardrails en option), `FakeLLMClient`, `make_client` — D1 |
| `agents/profile_weighting.py` | Profil → `WeightingResult` : poids bornés, resserrement seulement, thèmes, justification rattachée aux phrases du profil, preuves `FAIT` / `HYPOTHESE` — D2 |
| `agents/tools.py`, `agents/research.py` | 5 outils filtrés par `as_of` et journalisés ; candidats, titre demandé toujours analysé — D3 |
| `agents/debate/protocol.py`, `bull.py`, `realist.py`, `bear.py` | Tours 1 et 3 ; arguments sans preuve valide supprimés — D4 |
| `agents/explanation.py` | Rédaction, une relance, retrait des phrases fautives, assemblage de l'`Explanation` — D5 |
| `agents/simulated.py` (nouveau) | Agents simulés par des règles, pour l'exécution locale sans modèle |
| `agents/prompts/*.md` | 6 prompts en version `v1` |

**Explicabilité et gouvernance**

| Fichier | Contenu |
|---|---|
| `explain/fidelity.py` | Insertion des valeurs `{EV-…}`, 5 contrôles par affirmation, `FidelityReport`, recontrôle de la sortie — D5 |
| `explain/wording.py` | Filtre de formulations (`forbidden_wording.txt`) — D5 |
| `explain/trace.py` | `TraceRecorder` : étapes, statut, durée, échec visible — D6 |
| `engine/governance.py` | Panier simulé (taille, plafonds, groupes de concentration, déclassement motivé) et 3 points de contrôle — D6 |

**Moteur, validation, données (ajouts)**

| Fichier | Contenu |
|---|---|
| `engine/signals.py` | + `THEMES`, `preference_signals` : le critère `preferences` est maintenant couvert |
| `engine/decision.py` | + paramètre `candidates` de `decide` ; `apply_debate` (confiance, désaccords, drapeau « à examiner ») |
| `engine/coherence.py` | + `RISK_LIMITS`, `tolerance_level`, `limit_tensions`, `reference_medians` |
| `engine/scoring.py` | + `fit_level` (adéquation élevée / partielle / faible) |
| `validation/risk.py`, `validation/metrics.py` | + volatilité d'un panier simulé, preuve `SCENARIO` |
| `data/loaders.py` | + `load_reference_table` (ESG, arêtes du graphe) |
| `orchestration/pipeline.py`, `scripts/run_local.py` | Pipeline complet, `RunResult.save` ; CLI — C6, D7 |

**Tests** : `unit/test_wording.py` (16), `test_fidelity.py` (23), `test_llm_client.py` (12), `test_agents.py` (15), `test_governance.py` (11), `test_pipeline.py` (8), `tests/helpers.py` ; scénarios `test_s01`, `test_s03`, `test_s06`, `test_s08`, `test_s11`. Fixtures `forbidden`, `workspace`, `pipeline_run` dans `conftest.py`. Bilan `pytest` : 195 réussis, 4 en attente (S2, S10, `test_graph_edges`, S8 point 3).

**Données de référence** : `sources_registry.csv` + 2 lignes (`case_personas`, `easytrade_hypotheses`), sources des preuves de type `profile`.

**Documentation modifiée** : `docs/01_ARCHITECTURE.md` (étape 4 du flux), `docs/02_AGENTS.md`, `docs/03_DECISION_ENGINE.md`, `docs/05_EXPLICABILITE.md`, `docs/09_SCENARIOS_TEST.md`, `docs/ARBORESCENCE.md`, `README.md`, `backend/README.md`, ce fichier.

**Runs enregistrés** (`python scripts/run_local.py --tous --llm simule --save`, puis `--persona robert --ticker TSLA`) : `data/curated/runs/run_2026-11-12_{amira,mateo,robert,robert_TSLA}/`, non versionnés (régénérables, identiques à chaque exécution). Résultats : Amira, 7 pistes et 1 déclassée pour concentration (NVDA, plafond de 40 % atteint pour « Technologies ») ; Robert, 10 pistes, 2 cryptoactifs écartés par une règle ; Robert + TSLA, « incohérent avec le profil », 4 tensions chiffrées ; Mateo, « aucune recommandation » (ESG et qualité non sourcés).

**Non fait ou non vérifié**

- Aucun appel réel à Amazon Bedrock : `BedrockClient` n'est testé que sur une requête simulée. Les résultats ci-dessus viennent des agents simulés ; le taux de fidélité de 100 % mesure donc les règles simulées, pas un modèle. À refaire avec Bedrock dès que A2 est levé (`--llm bedrock`).
- Tour 2 du débat (extra n° 5), Bedrock Guardrails (extra n° 4 ; l'identifiant est seulement transmis s'il est configuré).
- `orchestration/handlers/*` (Lambda) et `scripts/run_scenarios.py` : toujours des squelettes (P4).
- Outils `chercher_documents` et `nouvelles` : aucune source branchée, ils répondent « rien » avec la raison. `preuves_esg` et `relations` lisent des fichiers encore vides (bloc G).
- `Python` : tests exécutés avec Python 3.13 (Anaconda) ; `backend/.venv` n'existe pas sur ce poste.

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

**Écarts avec les schémas P2** (résolus : `Explanation` suit le contrat depuis P3, et `api/service.py` traduit `ProfileWeights` — voir « Branchement mobile ↔ backend » plus haut) ; constat d'origine : `ProfileWeights` (`persona_id`/`constraints`/`rationale: str` contre `profile_id`/`hard_constraints`/liste) ; `Confidence` au masculin (`élevé`, `moyen`) contre le féminin de `docs/02_AGENTS.md` et du mobile (`élevée`, `moyenne`) ; `Rejection.rule` contre `RejectedItem.kind` ; `ScoredCandidate.criteria[]` contre `contributions` ; `CoherenceReport` (`Tension{dimension, detail, severe, evidence_id}`, `context: str`, `alternatives: tickers`) contre des `Claim` sourcés et des alternatives justifiées.

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
| S1 | Amira : le risque élevé garde une diversification | ✅ passe (local, agents simulés) | `test_s01` (5 tests) : pistes technologiques présentes (QQQ, GOOGL), plafonds tenus, 5 groupes hors technologies, NVDA déclassée pour concentration avec le motif rattaché au souhait de diversification du profil. Aucune piste crypto n'est retenue (classement, pas règle) |
| S2 | Mateo : l'ESG change le résultat | ⏳ non exécuté | Test en attente ; données ESG absentes. En attendant, le run de Mateo rend « aucune recommandation » et n'a aucune piste crypto (`test_pipeline`) |
| S3 | Robert : la demande incohérente est remise en question | ✅ passe (local, agents simulés) | `test_s03` (13 tests, TSLA et NVDA) : titre débattu, verdict « incohérent avec le profil », tensions chiffrées et sourcées (volatilité, perte maximale ; pire période de 3 ans pour TSLA), effet sur le panier simulé, alternatives, pistes par défaut sans crypto. Pour NVDA, la tension d'horizon ne se déclenche pas (sa pire période de 3 ans est positive) |
| S4 | « Aucune recommandation » | ✅ passe | `test_s04` : univers crypto-only exclu (Mateo) → aucun admissible ; et signaux manquants → preuves insuffisantes |
| S5 | Aucune fuite du futur | ✅ passe | `test_s05_aucune_fuite_du_futur.py` ; analyse à 2023-06-30 identique sur un jeu amputé du futur |
| S6 | Fidélité de l'explication | ✅ passe (local, agents simulés) | `test_s06` (15 tests). Taux au premier passage : Amira 20/20, Robert 28/28, Mateo sans objet (aucune piste rédigée) ; 124 affirmations recontrôlées dans les trois sorties, 0 écart. Avec un agent d'explication volontairement fautif : une relance, toutes les phrases fautives retirées, sortie fidèle. **Le taux avec un vrai modèle reste à mesurer** |
| S7 | Comparabilité (devises, calendriers, ajustements) | ✅ passe | 4 tests : CAD et dernier taux connu, adj_close, 7 fractionnements non réappliqués, 252 contre 365 |
| S8 | Formulation et cadre de simulation | ✅ passe | `test_s08` : aucune formulation refusée dans les sorties, le débat et la trace de 5 runs ; mention de simulation dans chaque `Explanation` ; point 3 vérifié sur les routes réelles (deux écritures seulement : profil fictif, analyse simulée ; aucun champ de transaction) |
| S9 | Exactitude et déterminisme des calculs | ✅ passe | Exécutions identiques ; XIU.TO, AAPL, BTC-USD recoupés par calcul sans pandas (tolérance relative 1e-9) |
| S10 | Graphe sourcé | ⏳ non exécuté | Test en attente ; aucune arête saisie |
| S11 | Désaccord conservé | ✅ passe | `test_s11` (5 tests, positions divergentes imposées par un faux client) : désaccord recopié dans `Decision.disagreements` et dans l'explication, confiance jamais « élevée », classement inchangé, arguments sans preuve valide supprimés ; si le débat s'oppose à toutes les pistes, aucune recommandation |
| S12 | Adaptation au profil | ✅ passe | `test_s12` : même univers (8 actifs réels), classements différents pour Amira et Robert, contributions alignées sur les poids, déterministe |

**Bilan : 10 passent (S1, S3, S4, S5, S6, S7, S8, S9, S11, S12), 0 échoue, 2 non exécutés (S2, S10).** S1, S3 et S6 passent en local avec des agents simulés ; ils sont à rejouer avec Bedrock.

### Tests techniques

| Test | État | Écart |
|---|---|---|
| `unit/test_reference_data.py` (5 tests : personas, poids normalisés, contraintes bornées, registre des sources, univers de 31 actifs) | ✅ 5 / 5 | — |
| Tests unitaires P1 : `test_fx_calendar`, `test_point_in_time`, `test_metrics`, `test_evidence_ledger`, `test_data_quality` | ✅ | — |
| Tests unitaires P2 : `test_constraints` (4), `test_scoring` (6) | ✅ | — |
| Tests unitaires P3 : `test_wording` (16), `test_fidelity` (23), `test_llm_client` (12), `test_agents` (15), `test_governance` (11), `test_pipeline` (8) | ✅ | — |
| Contrat mobile ↔ backend : `backend/tests/api` (51), `mobile/tests` (20), `npm run e2e:api` | ✅ | — |
| `test_graph_edges` (G) | ⏳ en attente | Squelette |
| Validité de tous les fichiers JSON et Python du dépôt | ✅ | — |

## 4. Tâches restantes, dans l'ordre

Cocher au fur et à mesure. Les blocs A et F peuvent avancer en parallèle des autres.

### A. Décisions et confirmations (bloquantes pour certaines tâches)

- [ ] A1. Confirmer dates limites, plateforme de dépôt et formats (consignes logistiques officielles).
- [x] A2. Compte AWS : atelier temporaire, us-east-1, Bedrock, modèles au choix, 500 $ de crédits. Vérifié le 2026-11-15 : `cdk bootstrap` et `cdk deploy` passent ; Lambda, Step Functions, API Gateway, S3, DynamoDB ouverts. Solde des crédits non visible depuis le compte (géré par les organisateurs) : suivre la dépense (Billing → Bills, Cost Explorer) contre 500 $.
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
- [x] C6. `orchestration/pipeline.py` sans LLM (débat simulé) ; `scripts/run_local.py`. Fait avec P3 (agents simulés).
- [ ] C7. Calibrer poids et contraintes de `personas.json` sur les résultats. Poids et contraintes inchangés en P3. À regarder : aucune piste crypto pour Amira (BTC et ETH sont mal classés sur 5 ans) ; NVDA déclassée au profit de QQQ et GOOGL ; repères de risque et seuils d'adéquation posés en P3 (`docs/03_DECISION_ENGINE.md`).

### D. Agents et explicabilité — P3

- [x] D1. `agents/llm_client.py` : Bedrock, sortie structurée, faux client de test.
- [x] D2. `agents/profile_weighting.py` + prompt.
- [x] D3. `agents/tools.py`, `agents/research.py` + prompt.
- [x] D4. `agents/debate/*` : tours 1 et 3 + prompts. → **S11**
- [x] D5. `agents/explanation.py`, `explain/fidelity.py`, `explain/wording.py`. → `test_fidelity`, `test_wording`, **S6**, **S8** (points 1 et 2)
- [x] D6. `explain/trace.py`, `engine/governance.py`.
- [x] D7. Scénarios **S1** et **S3** au vert en local ; runs des personas enregistrés dans `data/curated/runs/` (agents simulés).
- [ ] D8. **En cours (2026-11-15)** : identifiants d'atelier et modèles OK (rapide `us.anthropic.claude-haiku-5-5`, fort `us.anthropic.claude-sonnet-5-5`) ; 8 à 12 s par appel. Analyses par défaut des trois personas terminées sur AWS avec les vrais modèles (statut « termine » : vérificateur de fidélité passé). Reste : relever le taux de fidélité au premier passage (`fidelity.json` du run sur S3), rejouer les scénarios S1, S3, S6, relire les textes produits. Rejouer S1, S3, S6 avec Amazon Bedrock (`--llm bedrock`) dès que les identifiants du compte d'atelier sont disponibles (client corrigé en P4 : ni `temperature` ni `toolChoice` forcé, refusés par Opus 5.5 / Sonnet 5.5 / Haiku 5.5) : vérifier la requête Converse sur le compte réel, mesurer le taux de fidélité d'un vrai modèle, ajuster les prompts `v1`, puis réenregistrer les runs des personas.

### E. AWS — P4 (dès que A2 est levé)

- [x] E1. `DataStack` : S3 chiffré (données copiées au déploiement), DynamoDB ; `scripts/seed_aws.py`.
- [x] E2. `PipelineStack` : 8 Lambda (`orchestration/handlers/*`), machine d'états en série + `Map` du débat, droits Bedrock. Pipeline découpé en étapes (`stage_*`, `RunContext`), même code qu'en local.
- [x] E3. `ApiStack` : API Gateway HTTP + Lambda API ; `api/aws_service.py` (runs dans DynamoDB, lancement Step Functions, résultat sur S3, profils fictifs dans la table).
- [x] E4. Déployé le 2026-11-15 (`npx.cmd aws-cdk deploy --all`, sortie `EasyTradeApi.ApiUrl`) ; `/health` répond ; trois analyses complètes sur AWS en ~2 min chacune. Captures du graphe Step Functions pour la vidéo : à faire si ce n'est pas déjà fait (les exécutions restent visibles dans la console).
- [ ] E6. Précalculer les analyses sur AWS (`python scripts/precompute.py`, URL dans `EASYTRADE_API_URL` du `.env`) : **3 / 96 faites** (vues des 3 profils + analyses par défaut). Coût mesuré (CloudWatch, prix publics Anthropic) : 1,06 $ pour 3 analyses + 3 vues (Haiku 1 675 926 jetons en entrée / 275 932 en sortie ; Sonnet 270 153 / 21 540) ; ≈ 0,35 $ par analyse ⇒ ≈ 33 à 40 $ pour les 93 restantes. Reste : `python scripts/precompute.py --concurrency 5` (≈ 45 à 70 min).
- [x] E5. Un rôle IAM par fonction (compartiment, table, Bedrock seulement si besoin) ; aucun secret nécessaire (rôle de la fonction) ; étiquettes `projet`, `evenement`, `environnement`.

### F. Mobile — P5 (démarre tout de suite avec les données fictives)

- [x] F1. Initialiser le projet Expo (`mobile/README.md`) ; thème ; `SimulationBanner`.
- [x] F2. `src/types/contracts.ts`, `src/api/*` avec bascule données fictives / API.
- [x] F3. Profil : personas, questionnaire, résumé.
- [x] F4. Pistes à explorer : `MoveCard`, `FitBadge`, `RunProgress`, écartées, « aucune recommandation ».
- [x] F5. Fiche d'une piste : risque, débat, contributions, « ce que nous ne savons pas ».
- [x] F6. « Pourquoi ? » : `EvidenceChip`, écran preuve, parcours de l'analyse.
- [x] F7. Tester une idée.
- [x] F8. Graphe de dépendances, version radiale.
- [x] F9. Brancher l'API réelle : fait en local (`EXPO_PUBLIC_USE_MOCKS=false`, `uvicorn easytrade.api.app:app`). Contrat vérifié par `pytest tests/api`, `npm test` et `npm run e2e:api`.
- [ ] F9b. Essai sur téléphone avec Expo Go (URL de l'API : adresse IP locale de l'ordinateur), puis sur l'API déployée (E3).
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

## 7. Hypothèses prises à l'étape 3 (à valider par l'équipe)

Détail et valeurs : `docs/03_DECISION_ENGINE.md`, section « Hypothèses ajoutées à l'étape P3 ».

1. Un agent n'écrit aucun chiffre : il place `{EV-…}` et le code insère la valeur. Tolérance du vérificateur : l'arrondi à la dernière décimale écrite.
2. Panier simulé à parts égales ; nombre de pistes tiré de la part maximale par actif (7 pour Amira, 10 pour Mateo et Robert).
3. Trois groupes de concentration comptés ensemble pour le plafond par secteur (Technologies ; Actions américaines, marché large ; Obligations).
4. Critère `preferences` : 7 thèmes fermés, choisis par l'agent de pondération, rattachés aux actifs par le code.
5. Agent de pondération : ± 0,10 autour du gabarit ; il ne peut que resserrer une contrainte dure. Gabarit d'un profil fictif : le persona du même niveau de risque.
6. Repères de risque par tolérance, avec un niveau « faible à modérée » (22 % / −25 %) pour Robert ; tension sévère au-delà de 1,5 fois le repère.
7. Libellé d'adéquation : seuils 0,65 et 0,50 sur le score rapporté aux critères couverts.
8. Confiance d'une piste = minimum (couverture des données, accord du débat) ; « à examiner » si le Bear s'oppose en citant une preuve du profil.
9. Seuls les pistes pressenties, les candidats déclassés et le titre demandé sont débattus.
10. La présélection de l'agent de recherche ne change le score d'aucun actif (normalisation sur tout l'univers admissible).
11. Trace du débat : une étape par agent et par tour, tous candidats confondus (6 étapes), pas une étape par appel.
12. Si la sortie finale garde un écart de fidélité après retrait des phrases fautives, elle n'est pas affichée : le run échoue.
13. Deux sources internes ajoutées au registre : `case_personas` (phrases des profils) et `easytrade_hypotheses` (poids, plafonds, repères).

## 8. Hypothèses prises à l'étape 5 (à valider par l'équipe)

1. Données fictives par défaut (`EXPO_PUBLIC_USE_MOCKS=true`), signalées par un second bandeau ; aucun chiffre fictif dans la vidéo.
2. Champs de réponse proposés par le front (`mobile/README.md`, section Contrats) et 3 routes ajoutées : `GET /profiles/{id}`, `GET /assets`, `GET /data`.
3. Seuils indicatifs de risque par tolérance, affichés comme `HYPOTHESE` sur la fiche et dans « Tester une idée » : volatilité 18 / 25 / 45 %, perte maximale −20 / −30 / −50 % (faible / modérée / élevée). Valeurs du serveur fictif seulement ; à fixer dans le moteur (C7).
4. Effet sur le panier simulé : moyenne pondérée des volatilités sans corrélations (approximation signalée dans la preuve `SCENARIO`) ; à remplacer par le calcul du moteur.
5. Graphe : version radiale fixe, profondeur 1 ; la liste des relations sous le graphe donne le même contenu (accessibilité).
6. Poids modifiables sur l'écran de résumé par pas de 5 points, renormalisés ; la modification crée un nouveau profil (`POST /profiles` avec `base_persona` et `weights_override`).
7. Questionnaire : 3 gabarits (faible → Robert, modérée → Mateo, élevée → Amira) ajustés par les préférences et exclusions ; à reprendre par l'agent de pondération (D2).

## 9. Hypothèses prises au branchement mobile ↔ backend (à valider par l'équipe)

1. Le contrat de présentation est `mobile/src/types/contracts.ts` ; le backend s'y conforme par une couche de traduction (`api/service.py`), sans modifier les schémas internes du moteur.
2. Toute lecture de preuve, de fiche ou de graphe est rattachée à un run (`run_id`), parce que les identifiants de preuves sont propres à un run.
3. Même demande, même analyse : `run_id` est déterministe (`run_<date>_<profil>[_<titre>]`) et un run terminé est réutilisé. « Relancer l'analyse » rend donc le même résultat tant que les données n'ont pas changé.
4. Questionnaire → profil fictif : gabarit par tolérance (faible → Robert, modérée → Mateo, élevée → Amira) ; horizons court / moyen / long = 3 à 5 ans, 5 à 12 ans, 12 ans et plus ; chaque réponse devient une phrase de profil (preuve `FAIT`, source `profil_questionnaire`). Identifiant dérivé des réponses : même questionnaire, même profil.
5. Exclusions proposées : seulement celles que le moteur applique (crypto → part maximale 0 ; spéculatif → `exclu` ; controverses → exclusion ESG). « Actions individuelles » et « FNB » ont été retirées du questionnaire : le moteur n'a pas de règle d'exclusion par classe d'actifs.
6. Poids modifiés à la main : la variante prend ces poids comme gabarit (l'écart de ± 10 points de l'agent de pondération s'applique autour d'eux), les règles du profil d'origine sont conservées.
7. Repères de risque de la fiche : `RISK_LIMITS` du moteur, selon la tolérance du profil ; la fiche situe chaque indicateur entre le minimum et le maximum de l'univers à la même date.
8. Cinq étapes affichées pendant l'analyse, déduites de la trace : profil ; recherche et validation (fin de `recherche`) ; débat (`debate.*`) ; décision ; explication.
9. CORS ouvert à toutes les origines en local (`EASYTRADE_CORS_ORIGINS` pour restreindre) ; à restreindre au domaine de l'application une fois déployé.
