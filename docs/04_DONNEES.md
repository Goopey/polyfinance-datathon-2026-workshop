# 04 — Données

Critère « Analyse et traitement des données » (20 %) : le jury regarde la rigueur, la validation et la visualisation, pas le volume. Pour chaque donnée, on doit pouvoir dire pourquoi elle est là, d'où elle vient, comment elle est transformée et quelles sont ses limites.

## 1. Socle : le jeu de départ du datathon

Copié dans `data/raw/starter/` (fenêtre du 2021-11-12 au 2026-11-12, extraction le 2026-11-13).

| Fichier | Contenu | Clés |
|---|---|---|
| `assets_universe.csv` | 31 actifs : 10 actions CA, 10 US, 9 FNB, BTC, ETH | `asset_id, ticker, name, asset_class, market, currency, sector` |
| `prices_daily.csv` | ~40 000 lignes | `date, ticker, open, high, low, close, adj_close, volume, currency` |
| `corporate_actions.csv` | Dividendes et fractionnements | `ex_date, ticker, action, value, unit` |
| `fx_usdcad_daily.csv` | Change Banque du Canada | `date, usdcad, cadusd` |
| `macro_rates.csv` | 9 séries, format long | `date, series_id, value, unit, frequency, label, source` |
| `sources_metadata.csv` | Source, date, traitement, limites, conditions | — |
| `build_dataset.py` | Régénère les CSV | — |

### Pièges signalés par le README du jeu de départ → traitement chez nous

| Piège | Traitement | Module |
|---|---|---|
| Prix en devise de cotation (`.TO` en CAD, reste en USD) | Conversion en CAD pour toute agrégation ; devise conservée sur chaque preuve | `data/fx.py` |
| Pas de taux de change les jours fériés canadiens | Dernier taux connu reporté, report signalé | `data/fx.py` |
| Calendriers différents (TSX, US, crypto 7 j/7) | Alignement explicite et documenté ; rendements calculés par actif avant toute jointure | `data/calendar.py` |
| `adj_close` (dividendes + fractionnements) contre `close` | Rendements sur `adj_close` uniquement ; ne jamais réappliquer les fractionnements | `validation/metrics.py` |
| Lignes crypto = jours civils UTC | Annualisation sur 365 jours pour la crypto, 252 pour le reste, indiquée dans la preuve | `validation/metrics.py` |
| CNQ.TO : « fractionnement » de 1,021 le 2022-08-22 | Anomalie documentée ; vérification auprès des relations investisseurs avant usage | `validation/data_quality.py` |
| Macro mensuelle datée au mois de référence, pas à la publication | Délai de publication appliqué (`published_at`) ; valeurs FRED révisées signalées | `data/point_in_time.py` |
| Biais du survivant (univers choisi en 2026) | Limite affichée sur toute statistique historique | `explain/` |
| Aucune donnée ESG, nouvelle ou fondamentale | À ajouter avec sources documentées (section 2) | `ingestion/` |

## 2. Données à ajouter

| Besoin | Source | Usage | Priorité |
|---|---|---|---|
| Fondamentaux US | SEC EDGAR (données XBRL, 10-K, 10-Q) | Critère `qualite`, graphe | MVP |
| Relations fournisseurs / clients / concurrents | Dépôts 10-K (description de l'activité, facteurs de risque) ; SEDAR+ pour les émetteurs canadiens | Graphe de dépendances | MVP (5 à 8 sociétés) |
| ESG | Rapports de durabilité des sociétés ; méthodologie et composition du FNB ESGV publiées par l'émetteur ; dépôts réglementaires | Critère `esg`, exclusions de Mateo | MVP ; émissions de GES de 7 titres faites (section 12), le reste à saisir |
| Composition des FNB | Sites des émetteurs (fiches produits, titres détenus) | Diversification, transparence | MVP léger |
| Macro complémentaire | Banque du Canada, FRED, Statistique Canada | Contexte | Extra |
| Nouvelles datées | Communiqués des émetteurs, dépôts 8-K | Signaux, graphe | Extra |
| Sentiment | Dérivé des nouvelles ci-dessus | Jauge de sentiment | Extra |

### APIs envisagées par l'équipe : statut

| Source | Statut | Raison |
|---|---|---|
| Alpaca (données de marché) | **Optionnelle, derrière un interrupteur** | Conditions de redistribution à vérifier avant tout affichage ; uniquement les données, jamais l'API de courtage |
| Finnhub | **Optionnelle, derrière un interrupteur** | La page de tarification indique une licence « usage personnel » pour le plan gratuit ; à valider pour un prototype montré à un jury |
| Opinions d'experts | **Non retenue pour le MVP** | Licences de rediffusion, difficile à sourcer proprement |
| Suivi de portefeuilles crypto (wallets) | **Non retenue** | Risque de données liées à des personnes ; n'apporte pas de points sur la grille |

Aucune donnée brute issue de ces APIs n'est versionnée dans le dépôt. Voir `08_CONFORMITE.md`.

## 3. Registre des sources

`data/reference/sources_registry.csv` étend le `sources_metadata.csv` du jeu de départ. Une ligne par source, obligatoire avant toute utilisation :

`source_id, nom, url, type_de_donnee, date_extraction, couverture, frequence, traitements, limites, licence, conditions_url, redistribution_autorisee, statut, verifie_par, verifie_le`

`statut` ∈ `utilisé | prévu | optionnel — désactivé`. Les colonnes `verifie_par` et `verifie_le` sont remplies par la personne qui a relu les conditions d'utilisation.

## 4. Cohérence temporelle (point-in-time)

Règle : une analyse à la date `as_of` n'utilise que ce qui était **publié** à cette date.

Chaque enregistrement porte trois dates :

| Champ | Sens |
|---|---|
| `observed_at` | Période ou date que la donnée décrit |
| `published_at` | Date à laquelle elle est devenue accessible |
| `retrieved_at` | Date à laquelle nous l'avons extraite |

Application :

- Tout accès aux données passe par `data/point_in_time.py`, qui filtre sur `published_at ≤ as_of`. Aucun module ne lit les fichiers directement.
- Prix : `published_at` = date de clôture.
- Macro mensuelle : `published_at` = date de publication réelle si connue, sinon délai prudent documenté.
- Dépôts : `published_at` = date de dépôt, pas la fin de l'exercice.
- Nouvelles et ESG : date du document.
- Test automatique : scénario S5.

## 5. Schémas préparés (`data/curated/`)

| Table | Clés | Remarques |
|---|---|---|
| `prices` | `date, ticker` | `adj_close`, devise, `close_cad` |
| `returns` | `date, ticker` | Rendements quotidiens, calendrier propre à l'actif |
| `metrics` | `as_of, ticker, metric, window` | Sortie de la couche de validation |
| `fundamentals` | `ticker, period_end, published_at` | |
| `esg_evidence` | `ticker, document_date` | Type de signal, extrait court, lien, `claim_kind` |
| `graph_edges` | `source, target, relation` | Voir section 6 |
| `evidence` | `evidence_id` | Registre de preuves (voir `05_EXPLICABILITE.md`) |

Format : Parquet sur S3, CSV pour les fichiers de référence saisis à la main.

## 6. Données du graphe de dépendances

Une arête n'existe que si elle est sourcée.

| Champ | Exemple |
|---|---|
| `source`, `target` | `NVDA` → `TSM` |
| `relation` | `FOURNISSEUR`, `CLIENT`, `CONCURRENT`, `PARTENAIRE` |
| `claim_kind` | `FAIT` (document cité) ou `HYPOTHESE` |
| `document` | Type, identifiant du dépôt, section, date, URL |
| `excerpt` | Court extrait justificatif |
| `extracted_by` | `manuel` ou `llm+validation` |

- Les nœuds hors univers sont affichés comme contexte, sans métriques.
- Les relations extraites par LLM sont revues avant d'entrer dans le graphe.
- Les « prochains accords potentiels » sont des hypothèses : style visuel distinct, mention « hypothèse », jamais présentés comme des faits. Recommandation : hors MVP.

## 7. Contrôles qualité

Exécutés à l'ingestion ; résultats écrits dans `data/curated/quality_report.json` et montrés dans l'application (écran « Données »).

- Doublons `(date, ticker)`, prix nuls ou négatifs, volumes nuls.
- Trous de plus de N séances par actif.
- Variations sur une journée au-delà d'un seuil, rapprochées des opérations sur titres.
- Couverture du change sur toutes les dates utilisées.
- Nombre minimal d'observations par indicateur.
- Vérification croisée d'un échantillon d'indicateurs par calcul manuel (scénario S9).

## 8. Visualisation des données

- Courbes de prix ajustés en base 100, en CAD.
- Carte risque / rendement historique avec la position du profil.
- Contribution des critères au score.
- Graphe de dépendances.
- Chronologie des preuves (date de publication) pour montrer le respect du point-in-time.

## 9. Hypothèses de la couche données (P1)

Valeurs dans `backend/easytrade/config.py`. Ce sont des choix de l'équipe (`HYPOTHESE`), à réviser si une source officielle les contredit.

| Sujet | Valeur retenue | Raison |
|---|---|---|
| Délai de publication, IPC américain (`CPIAUCSL`) | 1 mois + 15 jours après le mois de référence | Publication habituelle vers le 10-15 du mois suivant ; délai prudent |
| Délai de publication, chômage américain (`UNRATE`) | 1 mois + 7 jours | Publié le premier vendredi du mois suivant |
| Délai de publication, IPC canadien (`STATIC_TOTALCPICHANGE`) | 1 mois + 25 jours | Publié vers la troisième semaine du mois suivant |
| Délai de publication, séries quotidiennes | 0 jour (Banque du Canada), 1 jour (FRED : `DFF`, `DGS2`, `DGS10`) | Publication le jour même ou le jour ouvrable suivant |
| Série macro sans délai connu | Refusée (erreur) | Ne jamais supposer une publication le jour même |
| Séances d'un calendrier | Union des dates observées pour les actifs du même marché (TSX, US, crypto) | Pas de liste de jours fériés codée en dur |
| Comparaison de deux actifs (corrélation) | Dates communes, rendements calculés après alignement, sans remplissage | Même intervalle de temps pour les deux actifs |
| Devise des indicateurs | CAD (`adj_close` × taux USD/CAD du jour, dernier taux connu sinon) | Agrégations en CAD ; devise indiquée sur chaque preuve |
| Week-ends crypto | Dernier taux de change connu (vendredi) | Pas de taux publié le week-end |
| Annualisation | 252 périodes (actions, FNB), 365 (crypto) | Calendrier propre à l'actif |
| Rendement annualisé | `(P_fin / P_début)^(périodes par an / nombre de rendements) − 1` | Géométrique, sur `adj_close` |
| Fenêtres d'indicateurs | Toute la période, 3 dernières années, dernière année ; pire période glissante de 1 et 3 ans ; année 2022 | 2022 : actions et obligations ont reculé ensemble |
| Indicateur « non calculé » | Moins de 30 rendements, ou historique plus court que la fenêtre glissante | Aucune preuve n'est créée pour une valeur absente |
| Trou de données | Plus de 5 séances consécutives manquantes | Seuil de contrôle |
| Variation journalière à signaler | Plus de 25 % en valeur absolue | Seuil de contrôle |
| Nombre minimal d'observations par actif | 252 | Une année de séances |
| Fractionnement suspect | Ratio inférieur à 1,5 (ou à l'inverse) | CNQ.TO 1,021 ; jamais appliqué, signalé dans les limites de chaque preuve du ticker |
| Concentration sectorielle | Hors P1 | Dépend d'un portefeuille, donc du moteur (P2) |

Rapport généré : `data/curated/quality_report.json` (commande `python scripts/bootstrap_data.py`). Résultat sur le jeu de départ : 6 contrôles sans remarque, 2 avertissements (volume nul de ZST.TO le 2022-07-06 ; anomalie CNQ.TO du 2022-08-22).

## 10. Fondamentaux et sociétés comparables (Finnhub, 2026-11-15)

Instantané de l'offre gratuite Finnhub, produit par `python scripts/fetch_finnhub.py` (clé `FINNHUB_API_KEY` dans
`.env`) et versionné. L'application et les Lambda lisent les fichiers, jamais l'API (pas de clé sur AWS, démonstration
reproductible, ADR 0002).

| Fichier | Contenu | Date utilisée |
|---|---|---|
| `data/reference/graph_edges.csv` | 90 arêtes `CONCURRENT` : jusqu'à 5 sociétés comparables par action, une arête par paire | `document_date` = 2026-11-12, claim `HYPOTHESE` : la classification n'est pas datée par Finnhub ; on suppose qu'elle était la même à la date d'analyse ; la date réelle du relevé est dans l'extrait |
| `data/reference/fundamentals.csv` | Séries annuelles `roe`, `totalDebtToEquity`, `netMargin` depuis 2018 (471 points) | Fin d'exercice ; publication supposée 90 jours plus tard (`FUNDAMENTALS_ANNUAL_LAG_DAYS`, config.py) |

- Couverture : les 20 actions. Les 10 canadiennes passent par leur cotation américaine (RY, TD, MFC, ENB, CNQ, CNI,
  FTS, SHOP, ANCTF, CNSWF) : accès gratuit, alors que le symbole de Toronto est payant. Ni FNB ni crypto.
- Comparables hors univers (BMO, AMD…) : nœuds de contexte du graphe, sans métriques. Une seule arête relie deux
  actifs de l'univers (RY.TO ↔ TD.TO) ; des liens de corrélation calculés sur nos prix pourront compléter le graphe
  (nouveau type de relation : changement du contrat mobile).
- Non disponible gratuitement chez Finnhub : scores ESG, chaînes d'approvisionnement, sentiment des nouvelles,
  historique de cours. Disponible et non encore utilisé : nouvelles d'entreprise récentes, recommandations
  d'analystes (mensuelles), sentiment des initiés (actions américaines).
- Pour rafraîchir : relancer le script, puis `python scripts/seed_aws.py` et redéployer, et vider les analyses
  précalculées (elles ne se mettent pas à jour seules).

## 11. Sentiment et cours affichés dans la fiche (2026-11-15)

**Sentiment** : `data/reference/sentiment.csv`, instantané `python scripts/fetch_finnhub.py --only sentiment`.

| Mesure | Couverture | Date de publication supposée |
|---|---|---|
| Recommandations d'analystes (achat fort … vente forte, mensuelles) | 20 actions ; l'offre gratuite ne donne que les 4 derniers mois | fin du mois (`SENTIMENT_ANALYST_LAG_DAYS`) |
| Indice de sentiment des initiés (MSPR, de -100 à +100) | 10 actions américaines (les dirigeants des sociétés canadiennes ne déposent pas de formulaire 4) | fin du mois + 5 jours (`SENTIMENT_INSIDER_LAG_DAYS`) |

- Lecture : `data/sentiment.py` ; l'API ne sert que le dernier mois publié à la date de la fiche
  (`AssetSheet.sentiment`), chaque chiffre devient une preuve `FAIT` du registre.
- Libellé « plutôt positif / neutre / plutôt négatif » : solde des analystes ≥ 0,5 / < 0,1 (hypothèse : les
  analystes penchent vers l'achat) ; l'indice des initiés sert seulement sans analyste.
- **Affichage seulement** : le sentiment n'entre ni dans le score ni dans la décision. FNB et crypto : `null`.

**Cours** : `GET /assets/{ticker}/prices`, calculé à partir du jeu de départ (aucune source nouvelle) : clôtures
ajustées converties en CAD jusqu'à la date d'analyse, dernier jour de cotation de chaque semaine (≈ 260 points sur
5 ans), variation sur la période et preuve du rendement annualisé sur la même fenêtre. Couvre les 31 actifs.

## 12. Preuves ESG : émissions directes de gaz à effet de serre (2026-11-15)

**Ce qui est fait** : un chargeur (`ingestion/esg.py`, `scripts/ingest_esg.py`) transforme deux fichiers publics en lignes de `data/reference/esg_evidence.csv`. Conditions d'utilisation, sources admises et règles de saisie : `CONTRIBUTING.md`, section « Données ESG ». Lecture des fichiers : `data/external_esg.py`. Sources au registre : `epa_ghgrp`, `canada_ghgrp`.

| Source | Année | Date de publication retenue | Titres couverts | `claim_kind` |
|---|---|---|---|---|
| EPA GHGRP (États-Unis) | 2023 | 2024-10-15 (date du fichier dans l'archive de l'EPA) | XOM, PG, GOOGL, TSLA | `FAIT` : la société mère et la part de détention sont déclarées par l'installation |
| ECCC GHGRP (Canada) | 2024 | 2026-05-27 (hypothèse, à confirmer sur la fiche open.canada.ca) | ENB.TO, CNQ.TO, FTS.TO | `HYPOTHESE` : rattachement par le nom de l'exploitant |

**Ce qui n'est pas couvert** : AAPL, MSFT, AMZN, JNJ, JPM et NVDA (aucune installation déclarante sous leur nom), RY, TD, MFC, CNR, ATD, SHOP, CSU (aucune installation déclarante sous leur nom au Canada), les 9 FNB et la crypto. Pour ces titres l'information est manquante, jamais « zéro ». Les trois autres dimensions de l'ESG (sociale, gouvernance, controverses) ne sont pas couvertes ; la composition d'ESGV et les rapports de durabilité restent à saisir (`etf_issuers`, `issuer_sustainability`, au statut « prévu »).

**Hypothèses de l'équipe** (valeurs dans `ingestion/esg.py` et `data/external_esg.py`)

| Sujet | Valeur retenue | Raison |
|---|---|---|
| Émissions EPA retenues | Somme de six onglets directs : installations ponctuelles, production pétrolière et gazière terrestre, collecte et compression, pipelines de transport, distribution locale, SF6 | La FAQ de l'EPA (question 12) les présente comme des catégories séparées du même programme. Les installations présentes dans deux onglets (34 sur 7 539) y déclarent des sources différentes. |
| Onglets exclus | « Suppliers », « CO2 Injection », « Geologic Sequestration » | Quantités liées aux produits vendus ou au CO2 injecté, pas des émissions directes |
| Part de détention EPA | Émission × part déclarée ; installation sans part déclarée exclue et signalée | Évite de choisir une part à la place de la société |
| Société mère EPA | Nom exact en majuscules (`EXXON MOBIL CORP`, `THE PROCTER & GAMBLE CO`, `ALPHABET INC`, `TESLA INC`) | Une recherche par mot ramène des faux positifs (« APPLETON PROPERTY VENTURES » pour Apple) |
| Rattachement canadien | Exploitant dont le nom commence par `Enbridge`, `Canadian Natural` ou `Fortis` | Le fichier donne « exploitant - installation », sans société mère ni part de détention |
| Total d'Enbridge | Borne inférieure (749,6 kt CO2e) | « Westcoast Energy Inc. » (1,17 Mt déclarées en 2024) n'est pas rattaché : le lien avec Enbridge n'est pas dans le fichier et reste à documenter |
| Dernière année canadienne | Année la plus récente du fichier ; refus si sa date de publication n'est pas dans `CANADA_PUBLISHED` | Évite de dater un nouveau jeu au hasard |
| Comparabilité EPA et ECCC | Non comparables directement | AR4 contre AR5, périmètres nationaux, rattachements de nature différente |
| Date d'extraction | Horodatage du nom du fichier canadien (2026-11-15), appliquée aux deux sources | Les trois fichiers ont été déposés le même jour |

**Contrôles** : la somme des gaz égale le « Total » du fichier canadien (écart maximal 2·10⁻⁹ t) ; le total des 1 879 installations de 2024 (291,66 Mt) correspond au rapport officiel d'ECCC (292 Mt) ; deux exécutions produisent le même fichier ; chaque ligne a une source « utilisé » au registre, une date valide et un titre de l'univers (`tests/unit/test_esg_ingestion.py`).

**Limite d'usage** : une ligne donne des tonnes absolues dans une phrase (`summary`) et pas un nombre séparé. Le moteur relit cette quantité avec `engine.esg.parse_emissions`, l'inverse exact du formatage du chargeur (aller-retour testé). Il n'en tire qu'un constat : « émetteur majeur documenté » (≥ 10 Mt CO2e). Il ne fait aucun classement par émissions, faute de normalisation par chiffre d'affaires et parce que les valeurs sont des bornes inférieures. Détail : docs/03, section « Critère ESG ».
