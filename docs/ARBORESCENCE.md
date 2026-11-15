# Arborescence complète

Générée à la fin de l'étape 0, mise à jour à la fin des étapes 5 (P5, `mobile/`) et 3 (P3, agents et tests). À régénérer quand la structure change.

```
easytrade/
├── backend/
│   ├── easytrade/
│   │   ├── agents/
│   │   │   ├── debate/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bear.py
│   │   │   │   ├── bull.py
│   │   │   │   ├── protocol.py
│   │   │   │   └── realist.py
│   │   │   ├── prompts/
│   │   │   │   ├── bear.md
│   │   │   │   ├── bull.md
│   │   │   │   ├── explanation.md
│   │   │   │   ├── profile_weighting.md
│   │   │   │   ├── realist.md
│   │   │   │   └── research.md
│   │   │   ├── __init__.py
│   │   │   ├── explanation.py
│   │   │   ├── llm_client.py
│   │   │   ├── profile_weighting.py
│   │   │   ├── research.py
│   │   │   ├── simulated.py
│   │   │   └── tools.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── deps.py
│   │   │   ├── routes_assets.py
│   │   │   ├── routes_profiles.py
│   │   │   ├── routes_runs.py
│   │   │   └── service.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── calendar.py
│   │   │   ├── external_esg.py
│   │   │   ├── fx.py
│   │   │   ├── loaders.py
│   │   │   ├── point_in_time.py
│   │   │   └── sources_registry.py
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── coherence.py
│   │   │   ├── constraints.py
│   │   │   ├── decision.py
│   │   │   ├── governance.py
│   │   │   ├── scoring.py
│   │   │   └── sensitivity.py
│   │   ├── explain/
│   │   │   ├── __init__.py
│   │   │   ├── evidence_ledger.py
│   │   │   ├── fidelity.py
│   │   │   ├── trace.py
│   │   │   └── wording.py
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── builder.py
│   │   │   └── edges.py
│   │   ├── ingestion/
│   │   │   ├── optional/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alpaca.py
│   │   │   │   └── finnhub.py
│   │   │   ├── __init__.py
│   │   │   ├── edgar.py
│   │   │   ├── esg.py
│   │   │   ├── etf_holdings.py
│   │   │   ├── macro.py
│   │   │   ├── news.py
│   │   │   └── starter_kit.py
│   │   ├── orchestration/
│   │   │   ├── handlers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── debate.py
│   │   │   │   ├── decision.py
│   │   │   │   ├── evidence_packs.py
│   │   │   │   ├── explanation.py
│   │   │   │   ├── ingestion.py
│   │   │   │   ├── profile.py
│   │   │   │   ├── research.py
│   │   │   │   └── validation.py
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── api.py
│   │   │   ├── candidate.py
│   │   │   ├── debate.py
│   │   │   ├── decision.py
│   │   │   ├── evidence.py
│   │   │   ├── explanation.py
│   │   │   ├── metrics.py
│   │   │   ├── profile.py
│   │   │   ├── trace.py
│   │   │   └── weights.py
│   │   ├── validation/
│   │   │   ├── __init__.py
│   │   │   ├── data_quality.py
│   │   │   ├── metrics.py
│   │   │   └── risk.py
│   │   ├── __init__.py
│   │   └── config.py
│   ├── tests/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   └── test_api_contract.py
│   │   ├── fixtures/
│   │   │   └── README.md
│   │   ├── scenarios/
│   │   │   ├── __init__.py
│   │   │   ├── test_s01_amira_diversification.py
│   │   │   ├── test_s02_mateo_esg.py
│   │   │   ├── test_s03_robert_demande_incoherente.py
│   │   │   ├── test_s04_aucune_recommandation.py
│   │   │   ├── test_s05_aucune_fuite_du_futur.py
│   │   │   ├── test_s06_fidelite_explication.py
│   │   │   ├── test_s07_comparabilite.py
│   │   │   ├── test_s08_formulation_simulation.py
│   │   │   ├── test_s09_exactitude_determinisme.py
│   │   │   ├── test_s10_graphe_source.py
│   │   │   ├── test_s11_desaccord_conserve.py
│   │   │   └── test_s12_adaptation_profil.py
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── test_agents.py
│   │   │   ├── test_constraints.py
│   │   │   ├── test_data_quality.py
│   │   │   ├── test_esg_ingestion.py
│   │   │   ├── test_evidence_ledger.py
│   │   │   ├── test_fidelity.py
│   │   │   ├── test_fx_calendar.py
│   │   │   ├── test_governance.py
│   │   │   ├── test_graph_edges.py
│   │   │   ├── test_llm_client.py
│   │   │   ├── test_metrics.py
│   │   │   ├── test_pipeline.py
│   │   │   ├── test_point_in_time.py
│   │   │   ├── test_reference_data.py
│   │   │   ├── test_scoring.py
│   │   │   └── test_wording.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── helpers.py
│   ├── pyproject.toml
│   ├── README.md
│   └── requirements.txt
├── data/
│   ├── curated/
│   │   └── .gitkeep
│   ├── raw/
│   │   ├── external/
│   │   │   └── .gitkeep
│   │   └── starter/
│   │       ├── assets_universe.csv
│   │       ├── build_dataset.py
│   │       ├── corporate_actions.csv
│   │       ├── data_quality_warnings.txt
│   │       ├── fx_usdcad_daily.csv
│   │       ├── macro_rates.csv
│   │       ├── prices_daily.csv
│   │       ├── README.md
│   │       └── sources_metadata.csv
│   ├── reference/
│   │   ├── esg_evidence.csv
│   │   ├── forbidden_wording.txt
│   │   ├── graph_edges.csv
│   │   ├── personas.json
│   │   └── sources_registry.csv
│   └── README.md
├── docs/
│   ├── adr/
│   │   ├── 0001-llm-argumentent-code-decide.md
│   │   ├── 0002-jeu-de-depart-socle-apis-optionnelles.md
│   │   ├── 0003-orchestration-step-functions-bedrock.md
│   │   ├── 0004-expo-react-native-export-web.md
│   │   ├── 0005-vocabulaire-simulation.md
│   │   └── README.md
│   ├── diagrammes/
│   │   └── architecture_agentique.txt
│   ├── livrables/
│   │   ├── documentation_technique.md
│   │   ├── one_pager.md
│   │   ├── pitch.md
│   │   ├── README.md
│   │   └── script_video.md
│   ├── 00_VISION.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_AGENTS.md
│   ├── 03_DECISION_ENGINE.md
│   ├── 04_DONNEES.md
│   ├── 05_EXPLICABILITE.md
│   ├── 06_AWS.md
│   ├── 07_UX_UI.md
│   ├── 08_CONFORMITE.md
│   ├── 09_SCENARIOS_TEST.md
│   ├── 10_PLAN.md
│   └── ARBORESCENCE.md
├── infra/
│   ├── stacks/
│   │   ├── __init__.py
│   │   ├── api_stack.py
│   │   ├── data_stack.py
│   │   ├── frontend_stack.py
│   │   ├── ingestion_stack.py
│   │   └── pipeline_stack.py
│   ├── statemachine/
│   │   └── pipeline.asl.json
│   ├── app.py
│   ├── cdk.json
│   ├── README.md
│   └── requirements.txt
├── mobile/
│   ├── e2e/
│   │   └── run.mjs
│   ├── scripts/
│   │   ├── contracts-schema.d.mts
│   │   └── contracts-schema.mjs
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx
│   │   │   ├── index.tsx
│   │   │   ├── profil.tsx
│   │   │   └── tester.tsx
│   │   ├── onboarding/
│   │   │   ├── index.tsx
│   │   │   ├── questionnaire.tsx
│   │   │   └── resume.tsx
│   │   ├── piste/
│   │   │   └── [ticker].tsx
│   │   ├── preuve/
│   │   │   └── [id].tsx
│   │   ├── run/
│   │   │   └── [id].tsx
│   │   ├── _layout.tsx
│   │   ├── comparer.tsx
│   │   ├── donnees.tsx
│   │   └── index.tsx
│   ├── assets/
│   │   ├── .gitkeep
│   │   ├── android-icon-background.png
│   │   ├── android-icon-foreground.png
│   │   ├── android-icon-monochrome.png
│   │   ├── favicon.png
│   │   ├── icon.png
│   │   └── splash-icon.png
│   ├── src/
│   │   ├── api/
│   │   │   ├── assets.ts
│   │   │   ├── client.ts
│   │   │   ├── profiles.ts
│   │   │   └── runs.ts
│   │   ├── components/
│   │   │   ├── ClaimTag.tsx
│   │   │   ├── ContributionBars.tsx
│   │   │   ├── DebateSummary.tsx
│   │   │   ├── EvidenceChip.tsx
│   │   │   ├── FitBadge.tsx
│   │   │   ├── GlossaryTerm.tsx
│   │   │   ├── MoveCard.tsx
│   │   │   ├── RiskMeter.tsx
│   │   │   ├── RunProgress.tsx
│   │   │   ├── SentimentGauge.tsx
│   │   │   ├── SimulationBanner.tsx
│   │   │   ├── SupplyChainGraph.tsx
│   │   │   ├── ui.tsx
│   │   │   └── UnknownsBlock.tsx
│   │   ├── hooks/
│   │   │   └── useBaseRun.ts
│   │   ├── i18n/
│   │   │   ├── fr.ts
│   │   │   └── glossaire.ts
│   │   ├── mocks/
│   │   │   ├── evidence.exemple.json
│   │   │   ├── explanation.exemple.json
│   │   │   ├── fixtures.ts
│   │   │   ├── graph.exemple.json
│   │   │   └── server.ts
│   │   ├── store/
│   │   │   ├── profile.ts
│   │   │   ├── settings.ts
│   │   │   └── storage.ts
│   │   ├── theme/
│   │   │   ├── tokens.ts
│   │   │   └── typography.ts
│   │   ├── types/
│   │   │   └── contracts.ts
│   │   └── format.ts
│   ├── tests/
│   │   ├── client.test.ts
│   │   ├── contracts.test.ts
│   │   └── tsconfig.json
│   ├── app.json
│   ├── contracts.schema.json
│   ├── metro.config.js
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   └── tsconfig.json
├── notebooks/
│   └── README.md
├── scripts/
│   ├── bootstrap_data.py
│   ├── ingest_esg.py
│   ├── run_local.py
│   ├── run_scenarios.py
│   └── seed_aws.py
├── .env.example
├── .gitignore
├── avancement.md
├── CONTRIBUTING.md
└── README.md
```
