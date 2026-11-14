# Backend EasyTrade

Paquet Python `easytrade` : données, validation déterministe, agents, moteur de décision, explicabilité, API.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
python ../scripts/run_local.py --persona amira --as-of 2026-11-12   # pipeline local (à implémenter)
uvicorn easytrade.api.app:app --reload                             # API locale (à implémenter)
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
| `api/` | Routes HTTP | `docs/01_ARCHITECTURE.md` |
