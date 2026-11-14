# EasyTrade

**Simulateur agentique d'aide à la décision d'investissement** — Datathon Polyfinances 2026, défi AlphaForge AI (Banque Nationale × AWS).

> Simulation uniquement. Aucune transaction réelle. Ceci n'est pas un conseil financier. Les profils sont fictifs.

EasyTrade présente, pour un profil d'investisseur donné, des pistes à explorer classées selon leur adéquation au profil. Chaque piste est expliquée à partir de données publiques datées et sourcées, et l'utilisateur peut tester une idée pour savoir si elle est cohérente avec son profil.

## État du projet

Étape 0 terminée : arborescence, conception, scénarios de test. Le code métier est à l'état de squelette. L'avancement détaillé et l'ordre des tâches sont dans [`avancement.md`](avancement.md).

## Idée directrice

**Les LLM argumentent, le code décide.**

```
Profil ─► 1. Pondération du profil ─► ┌ 2. Recherche (LLM + outils) ┐ ─► 3. Débat Bull / Réaliste / Bear
                                      └ Validation financière (code)┘        │
                                                                             ▼
                       Sortie expliquée ◄─ 5. Explication (LLM, vérifiée) ◄─ 4. Moteur de décision (code)
```

- Les chiffres viennent d'une couche Python déterministe.
- La décision vient d'un moteur à règles et à poids, dictés par le profil.
- Les modèles interprètent, cherchent, argumentent et rédigent ; chaque affirmation cite une preuve.

## Démarrage

Ce qui fonctionne aujourd'hui :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pytest -rs          # 5 tests de données de référence passent ; le reste est en attente
```

À venir (voir `avancement.md`) : pipeline local (`scripts/run_local.py`), API (`uvicorn easytrade.api.app:app`), application mobile (`mobile/README.md`), déploiement AWS (`infra/README.md`).

Configuration : copier `.env.example` en `.env`.

## Structure du dépôt

```
easytrade/
├── README.md              Ce fichier
├── avancement.md          Suivi : fichiers, scénarios, tâches restantes dans l'ordre
├── CONTRIBUTING.md        Règles de travail et commandes
├── .env.example           Variables de configuration (aucun secret versionné)
│
├── docs/                  Conception
│   ├── 00_VISION.md           North star, question traitée, alignement sur la grille
│   ├── 01_ARCHITECTURE.md     Du diagramme aux modules, flux, contrats, API
│   ├── 02_AGENTS.md           Une fiche par agent : pourquoi il existe, entrées, sorties, garde-fous
│   ├── 03_DECISION_ENGINE.md  Poids par profil, contraintes, score, « aucune recommandation »
│   ├── 04_DONNEES.md          Sources, licences, point-in-time, traitements, qualité
│   ├── 05_EXPLICABILITE.md    Registre de preuves, trace, vérificateur de fidélité
│   ├── 06_AWS.md              Services, rôle de chacun, ce qui se voit en démo
│   ├── 07_UX_UI.md            Parcours, écrans, graphe de dépendances, rédaction
│   ├── 08_CONFORMITE.md       Règles du défi → mécanismes → tests ; registre des risques
│   ├── 09_SCENARIOS_TEST.md   Scénarios S1 à S12 (définition de « ça marche »)
│   ├── 10_PLAN.md             Phases, répartition, MVP et extras
│   ├── ARBORESCENCE.md        Arborescence complète, fichier par fichier
│   ├── adr/                   Décisions d'architecture
│   ├── diagrammes/            Diagramme agentique d'origine
│   └── livrables/             Trames : vidéo, documentation technique, one-pager, pitch
│
├── data/
│   ├── raw/starter/           Jeu de départ du datathon (non modifié)
│   ├── raw/external/          Extractions de sources ajoutées (non versionné)
│   ├── curated/               Tables préparées (régénérables)
│   └── reference/             Personas, registre des sources, ESG, arêtes du graphe
│
├── backend/               Paquet Python `easytrade`
│   ├── easytrade/
│   │   ├── schemas/           Contrats JSON entre étapes
│   │   ├── data/              Accès aux données, filtre point-in-time
│   │   ├── ingestion/         Chargement des sources (optional/ : Alpaca, Finnhub désactivés)
│   │   ├── validation/        Couche de validation financière — sans LLM
│   │   ├── graph/             Graphe de dépendances
│   │   ├── agents/            Agents LLM, débat, prompts
│   │   ├── engine/            Moteur de décision — sans LLM
│   │   ├── explain/           Preuves, trace, fidélité, formulations
│   │   ├── orchestration/     Pipeline local + points d'entrée Lambda
│   │   └── api/               Routes HTTP
│   └── tests/
│       ├── unit/
│       └── scenarios/         Un test par scénario S1 à S12
│
├── mobile/                Application Expo / React Native
│   ├── app/                   Écrans : profil, pistes, fiche, tester une idée, preuve, parcours
│   └── src/                   Composants, API, types, thème, textes, données fictives
│
├── infra/                 AWS CDK (Python)
│   ├── stacks/                Data, Pipeline, Api, Ingestion, Frontend
│   └── statemachine/          Définition Step Functions du pipeline
│
├── scripts/               Données, exécution locale, scénarios, chargement AWS
└── notebooks/             Exploration seulement
```

## Données

| Source | Usage | État |
|---|---|---|
| Jeu de départ du datathon (Yahoo Finance via yfinance, Banque du Canada, FRED) | Prix, opérations sur titres, change, macro — 2021-11-12 au 2026-11-12 | Présent dans `data/raw/starter/` |
| SEC EDGAR, SEDAR+ | Fondamentaux, relations du graphe | Prévu |
| Sites des émetteurs de FNB, rapports de durabilité | Composition, ESG | Prévu |
| Alpaca, Finnhub | Optionnel | Désactivé tant que les conditions d'utilisation ne sont pas vérifiées |

Chaque source a une ligne dans `data/reference/sources_registry.csv` (origine, date, traitements, limites, conditions). Détail : `docs/04_DONNEES.md`.

## Conformité

Simulation, vocabulaire non prescriptif, distinction fait / hypothèse / scénario, aucune fuite du futur, licences documentées. Détail et liste de contrôle : `docs/08_CONFORMITE.md`.

## Livrables du datathon

Prototype + code + README, vidéo d'environ 5 minutes, documentation technique, one-pager. Trames dans `docs/livrables/`.

## Équipe

_À compléter._
