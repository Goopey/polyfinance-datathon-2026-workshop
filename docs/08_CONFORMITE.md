# 08 — Conformité et gouvernance

Source : section « Encadrement responsable » du case et diapositive « Le cadre responsable ».

## Règles du défi → mécanismes → tests

| Règle | Mécanisme dans EasyTrade | Test |
|---|---|---|
| Simulation uniquement, aucune transaction réelle | Aucune intégration de courtage ; aucun bouton d'ordre ; `SimulationBanner` permanent | S8 |
| Ne pas se présenter comme un conseil financier personnalisé | Vocabulaire non prescriptif ; profils fictifs ; mention sur chaque résultat ; Bedrock Guardrails | S8 |
| Aucune donnée bancaire confidentielle ni compte client réel | Aucun champ nominatif ; aucun compte ; personas ou profils fictifs | Revue |
| Distinguer faits, hypothèses, scénarios fictifs | `claim_kind` sur chaque preuve ; étiquettes à l'écran | S10 |
| Présenter les incertitudes importantes | Bloc « Ce que nous ne savons pas » ; niveau de confiance ; désaccords conservés | S11 |
| Explications synthétiques, vérifiables, fidèles | Registre de preuves ; vérificateur de fidélité | S6 |
| Ne pas inventer de justification après coup | L'explication ne peut citer que les preuves et étapes du run | S6 |
| Ne pas exposer le raisonnement interne des modèles | On enregistre entrées, outils, sorties ; arguments courts et sourcés | Revue |
| Ne pas prédire les rendements futurs | Indicateurs historiques libellés comme tels ; aucun prix cible ; aucun modèle de prévision | S8 |
| Ne pas assimiler automatiquement un profil à un actif | Score multi-critères ; contraintes explicites ; sensibilité | S12 |
| Cohérence temporelle | Accès aux données uniquement via le filtre point-in-time | S5 |
| Traçabilité, comparabilité | Registre des sources ; traitements documentés | S7 |
| Respect des licences | Registre des sources avec conditions ; APIs tierces derrière un interrupteur | Revue |

## Fonction de gouvernance

Le case suggère de rendre les contrôles visibles. Trois points de contrôle, chacun inscrit dans la trace :

1. **Avant le débat** : contraintes dures du profil appliquées, candidats sans preuve écartés.
2. **À la décision** : plafonds, tensions profil / demande, sortie « aucune recommandation » si les preuves manquent.
3. **Avant l'affichage** : vérificateur de fidélité, filtre de formulations.

L'écran « Parcours de l'analyse » liste ces contrôles et leur résultat.

## Registre des risques sur les fonctionnalités demandées

| Fonctionnalité du brief | Risque | Niveau | Décision proposée |
|---|---|---|---|
| « Next-trade counselor », « best moves » | Lecture comme conseil personnalisé | Élevé | Reformuler en « pistes à explorer » ; adéquation au profil, jamais d'injonction |
| Nom « EasyTrade » | Évoque l'exécution de transactions | Moyen | Sous-titre + bandeau de simulation ; à trancher en équipe |
| Alpaca | Fournisseur lié au courtage ; conditions de redistribution des données | Élevé | Données seulement, jamais l'API d'ordres ; optionnel ; conditions à vérifier avant affichage |
| Finnhub | Plan gratuit sous licence d'usage personnel | Moyen | Optionnel ; vérifier que l'usage en prototype de concours est couvert ; sinon s'en passer |
| Suivi de portefeuilles crypto | Adresses pouvant être rattachées à des personnes | Élevé | Non retenu |
| Opinions d'experts | Licences de rediffusion ; lecture comme prévision | Moyen | Non retenu pour le MVP |
| Jauge de sentiment | Fuite du futur si les nouvelles ne sont pas datées ; signal fragile | Moyen | Extra ; nouvelles datées uniquement ; limite affichée |
| « Prochains accords potentiels » dans le graphe | Spéculation présentée comme un fait | Élevé | Hors MVP ; sinon étiquette « Hypothèse » obligatoire |
| Relations du graphe extraites par LLM | Relation inventée | Moyen | Document cité obligatoire ; revue avant intégration |
| Classement fondé sur le rendement passé | Lecture comme prévision | Moyen | Libellé « observé de … à … » ; critère parmi sept ; limite affichée |
| Analyse fondamentale | Date de dépôt confondue avec fin d'exercice | Moyen | `published_at` = date de dépôt |
| Données du jeu de départ (Yahoo via yfinance) | Redistribution dans un dépôt public | Faible à moyen | Dépôt privé, ou régénération par `build_dataset.py` ; conditions citées |

## Liste de contrôle avant remise

- [ ] Bandeau de simulation visible sur tous les écrans et dans la vidéo.
- [ ] Aucune formulation prescriptive dans l'application, la vidéo, le one-pager.
- [ ] Toutes les sources ont une ligne complète dans `sources_registry.csv`, conditions d'utilisation vérifiées.
- [ ] Aucune clé d'API ni donnée brute sous licence restrictive dans le dépôt.
- [ ] S5 (point-in-time) et S6 (fidélité) passent.
- [ ] Chaque arête du graphe affichée en démo a un document cité.
- [ ] Les limites (fenêtre de 5 ans, biais du survivant, données ESG partielles) figurent dans la documentation et à l'écran.
- [ ] Les poids et seuils sont présentés comme des hypothèses de l'équipe.
- [ ] La vidéo montre deux personas contrastés et au moins un cas où le système dit non ou « je ne sais pas ».
