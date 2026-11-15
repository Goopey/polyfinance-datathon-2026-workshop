# Travailler dans ce dépôt

## Branches

- `main` : toujours démontrable.
- Une branche par tâche : `data/…`, `engine/…`, `agents/…`, `aws/…`, `mobile/…`, `docs/…`.
- Fusion par demande de tirage courte, relue par une autre personne quand c'est possible.

## Règles non négociables

1. **Aucun accès direct aux fichiers de données** hors de `easytrade/data/`. Tout passe par le filtre point-in-time.
2. **Aucun chiffre produit par un LLM.** Les chiffres viennent de `easytrade/validation/`.
3. **Toute nouvelle source** a sa ligne dans `data/reference/sources_registry.csv` avant d'être utilisée.
4. **Aucune clé** dans le dépôt.
5. **Vocabulaire** : voir la table de rédaction dans `docs/07_UX_UI.md`.

## Données ESG : conditions d'utilisation

Aucun jeu ESG par société n'est fourni avec le datathon. Les preuves ESG du dépôt viennent de deux fichiers publics d'émissions de gaz à effet de serre, transformés par `scripts/ingest_esg.py` en lignes de `data/reference/esg_evidence.csv`. Elles décrivent la dimension environnementale seulement (ni sociale ni gouvernance).

### Sources admises

| Source | Fichier à déposer dans `data/raw/external/` | Licence et conditions | Obligation |
|---|---|---|---|
| EPA, Greenhouse Gas Reporting Program (États-Unis), `source_id` `epa_ghgrp` | « 2023 Data Summary Spreadsheets » (`*data_summary_spreadsheets*.zip`) et « Reported Parent Companies » (`ghgp_data_parent_company*.csv`), page <https://www.epa.gov/ghgreporting/data-sets> | Documents de l'EPA : usage non commercial, scientifique et éducatif libre ; usage commercial non garanti ; des documents individuels peuvent avoir d'autres conditions (<https://www.epa.gov/web-policies-and-procedures/epa-disclaimers>) | Citer l'EPA comme source ; ne jamais suggérer son aval. Si le projet sort du cadre du datathon ou devient commercial, revoir cette source avant de la garder. |
| ECCC, Programme de déclaration des GES (Canada), `source_id` `canada_ghgrp` | « Greenhouse Gas (GHG) Emissions Data by Facility » (`GHGRP_UTF-8_EN_*.csv`), <https://open.canada.ca/data/en/dataset/a8ba14b7-7f23-462a-bdbb-83b0ef629823> | Licence du gouvernement ouvert – Canada, version 2.0 : usage libre, y compris commercial (<https://open.canada.ca/en/open-government-licence-canada>) | **Attribution obligatoire** : « Contains information licensed under the Open Government Licence – Canada. » Ne pas suggérer l'aval du gouvernement ; ne pas utiliser ses logos. |

`owid-co2-data.csv` (Our World in Data) peut se trouver dans le même dossier : il donne des émissions par **pays**, aucune par société. Il n'est pas au registre et ne doit pas servir à qualifier une société.

### Ce qui est interdit

- Cotes ou scores ESG commerciaux (MSCI, Sustainalytics, LSEG, S&P Global, ISS, etc.) et tout extrait : ces données sont vendues sous licence commerciale, en général sans droit de redistribution. Sans licence lue et conservée, on ne les utilise pas.
- Jeux ESG tiers dont l'origine ou la licence n'est pas établie (dépôts GitHub ou Kaggle sans licence claire).
- Versionner un fichier de `data/raw/external/` (le `.gitignore` les exclut : ne pas forcer l'ajout).
- Modifier à la main une ligne dont `entered_by` vaut `script:ingest_esg` : elle serait réécrite à la prochaine exécution.
- Présenter l'absence de donnée comme une bonne nouvelle.

### Obtenir les fichiers et régénérer les preuves

1. Télécharger les trois fichiers aux adresses du tableau, dans `data/raw/external/`.
2. Lire les conditions de chaque source, puis renseigner `verifie_par` et `verifie_le` dans les lignes `epa_ghgrp` et `canada_ghgrp` de `data/reference/sources_registry.csv`. Ces deux champs sont vides à dessein : ils doivent être remplis par la personne qui a lu les conditions.
3. `python scripts/ingest_esg.py --dry-run` affiche l'audit (installations retenues par titre, contrôles) sans rien écrire. Sans `--dry-run`, le fichier est écrit. Les lignes saisies à la main sont conservées.
4. Lancer `pytest`, puis mettre à jour `avancement.md`.

Le lecteur d'Excel demande `openpyxl` (dans `backend/requirements.txt`).

### Écrire ou ajouter une ligne dans `esg_evidence.csv`

- `document_date` : la date de **publication** du document, jamais la période qu'il décrit. Elle sert de `published_at` : c'est ce qui empêche d'utiliser une donnée avant sa sortie (S5).
- `claim_kind` : `FAIT` si le document dit lui-même ce que la ligne affirme (par exemple la société mère déclarée par l'installation) ; `HYPOTHESE` quand l'équipe fait le lien (par exemple un rattachement par le nom de l'exploitant). Jamais `SCENARIO`.
- `source_id` : doit exister dans le registre avec le statut `utilisé`. Sinon l'outil `preuves_esg` ignore la ligne et le signale dans la trace.
- `excerpt` : court, fidèle au document. Un chiffre est celui du document ou celui d'un calcul reproductible par le script. Jamais un chiffre estimé ou produit par un modèle.
- Information absente : pas de ligne. Un titre sans installation déclarante n'est pas « à zéro émission » : son information est manquante.
- `entered_by` : le nom de la personne pour une saisie manuelle. `script:ingest_esg` est réservé au chargeur.

### Limites à rappeler dans toute présentation

- Chiffres absolus (Mt CO2e), non rapportés au chiffre d'affaires ni à la production : ils ne comparent pas des sociétés de tailles différentes.
- Périmètre national : États-Unis pour l'EPA, Canada pour ECCC. XOM n'est vu que par sa part américaine.
- Émissions directes seulement. L'EPA calcule avec les potentiels de réchauffement AR4, ECCC avec AR5 : les deux séries ne s'additionnent pas.
- Années 2023 (EPA) et 2024 (ECCC), antérieures à la date d'analyse.
- Rattachement canadien par le nom de l'exploitant : une filiale sous un autre nom est omise (« Westcoast Energy Inc. » pour Enbridge), donc le total d'ENB est une borne inférieure.
- Ces preuves ne notent pas encore le critère `esg` : le moteur le traite toujours comme « non sourcé » (scénario S2 non fait).

### Attribution à afficher

Partout où des données canadiennes sont montrées ou publiées (écran de la preuve, documentation technique, one-pager, vidéo) : « Contains information licensed under the Open Government Licence – Canada. » Pour l'EPA : « Source : U.S. Environmental Protection Agency, Greenhouse Gas Reporting Program. » Ces mentions ne sont pas encore ajoutées à l'application ni aux livrables.

## Après chaque étape terminée

Mettre à jour `avancement.md` : fichiers touchés, scénarios (passe / échoue + écart), tâches restantes.

## Commandes

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                       # tous les tests
pytest tests/scenarios -rs   # scénarios S1 à S12
pytest tests/api             # contrat mobile ↔ backend
uvicorn easytrade.api.app:app --port 8000   # API locale
python ../scripts/ingest_esg.py --dry-run   # preuves ESG depuis data/raw/external/ (voir « Données ESG »)

# Mobile
cd mobile && npm install && npx expo start
npm run typecheck && npm test   # types, contrat mobile ↔ backend, client HTTP
npm run e2e:api                 # parcours complet dans un navigateur, sur l'API réelle (e2e:mock : données fictives)
npm run contracts               # après toute modification de src/types/contracts.ts
```

Changer un champ échangé entre le mobile et le backend : modifier `mobile/src/types/contracts.ts` **et** le schéma Pydantic (`backend/easytrade/schemas/`), lancer `npm run contracts`, puis les tests des deux côtés.
