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
| ESG | Rapports de durabilité des sociétés ; méthodologie et composition du FNB ESGV publiées par l'émetteur ; dépôts réglementaires | Critère `esg`, exclusions de Mateo | MVP |
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
