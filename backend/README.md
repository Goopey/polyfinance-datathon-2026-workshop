# Backend EasyTrade

Paquet Python `easytrade` : données, validation déterministe, agents, moteur de décision, explicabilité, API.

```bash
# Python 3.11 ou plus requis (pyproject.toml). Avec uv : uv venv --python 3.12 .venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
python ../scripts/bootstrap_data.py                                 # tables préparées et rapport de qualité dans data/curated/
python ../scripts/run_local.py --persona amira --as-of 2026-11-12   # pipeline local complet (agents simulés sans Bedrock)
python ../scripts/run_local.py --persona robert --ticker TSLA -v    # « Tester une idée »
python ../scripts/run_local.py --tous --save                        # enregistre les runs des 3 personas dans data/curated/runs/
uvicorn easytrade.api.app:app --reload --port 8000                 # API locale (documentation interactive : /docs)
pytest tests/api                                                   # contrat mobile ↔ backend (mobile/contracts.schema.json)
```

| Dossier | Rôle | Conception |
|---|---|---|
| `schemas/` | Contrats JSON entre étapes | `docs/02_AGENTS.md` |
| `data/` | Accès aux données, filtre point-in-time | `docs/04_DONNEES.md` |
| `ingestion/` | Chargement des sources | `docs/04_DONNEES.md` |
| `validation/` | Couche de validation financière, sans LLM | `docs/02_AGENTS.md` |
| `graph/` | Graphe de dépendances | `docs/04_DONNEES.md` §6 |
| `agents/` | Agents LLM et prompts | `docs/02_AGENTS.md` |
| `engine/` | Moteur de décision, sans LLM | `docs/03_DECISION_ENGINE.md` |
| `explain/` | Registre de preuves, trace, fidélité | `docs/05_EXPLICABILITE.md` |
| `orchestration/` | Pipeline local et points d'entrée Lambda | `docs/01_ARCHITECTURE.md` |
| `api/` | Routes HTTP ; `service.py` exécute le pipeline et traduit vers les contrats du mobile (`schemas/api.py`) | `docs/01_ARCHITECTURE.md` |
