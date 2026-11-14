# Données

| Dossier | Contenu | Versionné |
|---|---|---|
| `raw/starter/` | Jeu de départ du datathon, non modifié | Oui si dépôt privé (voir plus bas) |
| `raw/external/` | Extractions de sources ajoutées (EDGAR, émetteurs de FNB, etc.) | Non |
| `curated/` | Tables préparées (Parquet), rapport de qualité | Non (régénérable) |
| `reference/` | Personas, registre des sources, preuves ESG, arêtes du graphe, termes interdits | Oui |

## Règles

- `raw/` n'est jamais modifié à la main. Les traitements vivent dans `backend/easytrade/`.
- Chaque source a une ligne dans `reference/sources_registry.csv`.
- Si le dépôt devient public : retirer `raw/starter/*.csv` et les régénérer avec `raw/starter/build_dataset.py`, les prix venant de Yahoo Finance sous ses propres conditions.

Conception complète : `docs/04_DONNEES.md`.
