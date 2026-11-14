# 07 — UX / UI

Cible : mobile d'abord, React Native. Référence d'ambiance : applications d'épargne grand public épurées. Critère UX/UI (10 %) : intuition, ergonomie, clarté.

## Principes

1. **Un écran, une idée.** Une seule action principale par écran.
2. **Compréhensible sans jargon.** Chaque terme technique a une traduction en une phrase (« Perte maximale : la pire baisse observée entre un sommet et un creux »).
3. **Le pourquoi à un geste.** Tout chiffre ouvre sa preuve.
4. **Deux niveaux de lecture.** Simple par défaut ; Avancé révèle les indicateurs détaillés.
5. **L'incertitude se voit.** Hypothèses, scénarios et informations manquantes sont visibles sans fouiller.
6. **Jamais prescriptif.** Voir la section Rédaction.

## Parcours

```
Premier lancement                    Lancements suivants
┌──────────────┐                     ┌──────────────────┐
│ Bienvenue    │                     │ Pistes à explorer│◄───────────┐
│ (simulation) │                     │ (accueil)        │            │
└──────┬───────┘                     └───┬──────────┬───┘            │
       ▼                                 ▼          ▼                │
┌──────────────┐                 ┌────────────┐ ┌───────────────┐    │
│ Votre profil │                 │ Fiche d'une│ │ Tester une    │    │
│ persona ou   │────────────────►│ piste      │ │ idée          │    │
│ questionnaire│                 └─────┬──────┘ └───────┬───────┘    │
└──────────────┘                       ▼                ▼            │
                                 ┌────────────┐  ┌──────────────┐    │
                                 │ Pourquoi ? │  │ Analyse de   │────┘
                                 │ preuves    │  │ cohérence    │
                                 └────────────┘  └──────────────┘
```

## Écrans

### 1. Profil (premier lancement)

- Choix rapide : trois cartes de personas (Amira, Mateo, Robert), ou « Créer un profil fictif ».
- Questionnaire : 5 questions, une par écran : objectif, horizon, tolérance au risque (illustrée par une baisse simulée), préférences, exclusions.
- Résultat : « Voici comment nous avons compris votre profil » — poids et règles affichés en clair, modifiables. C'est la sortie de l'agent de pondération.
- Mention : profil fictif, aucune donnée personnelle demandée.

### 2. Pistes à explorer (accueil)

- En haut : rappel du profil en une ligne et date des données.
- Liste de cartes. Chaque carte : nom, type d'actif, **adéquation au profil** (élevée / partielle / faible), une phrase de justification, niveau de confiance, indicateur de désaccord du débat.
- Section repliable « Écartées et pourquoi ».
- Pendant l'analyse : progression par étapes (Profil → Recherche et validation → Débat → Décision → Explication), alimentée par l'état réel de l'exécution.
- Bouton flottant « Tester une idée ».
- État « Aucune recommandation » : écran dédié expliquant ce qui manque.

### 3. Fiche d'une piste

Dans l'ordre de défilement :

1. **Aperçu** : nom, adéquation, trois raisons sourcées.
2. **Graphe de dépendances** (fonctionnalité phare, voir ci-dessous).
3. **Risque** : volatilité, perte maximale, pire période sur l'horizon, comparés au profil.
4. **Débat** : trois cartes Bull / Réaliste / Bear, position finale, désaccords.
5. **Signaux** : ESG, nouvelles datées, jauge de sentiment (extra).
6. **Pourquoi ce classement** : contribution de chaque critère.
7. **Ce que nous ne savons pas** : limites et informations manquantes.

### 4. Tester une idée

- Recherche d'un titre → analyse de cohérence avec le profil.
- Résultat : verdict, tensions chiffrées, effet sur le panier simulé, alternatives étayées.
- Démonstration directe du test Robert.

### 5. Pourquoi ? (preuve)

- Feuille modale : énoncé, valeur, source, dates d'observation, de publication et d'extraction, traitement, limites, étiquette Fait / Hypothèse / Scénario.
- Lien « Parcours de l'analyse » : étapes exécutées.

### 6. Comparer les profils (pour la vidéo)

- Deux personas côte à côte sur le même univers : classements, règles appliquées, différences surlignées.

### 7. Données

- Sources utilisées, dates d'extraction, limites, résultat des contrôles qualité.
- Chronologie des preuves d'une analyse par date de publication.

## Fonctionnalité phare : graphe de dépendances

Objectif : montrer en un coup d'œil dans quel écosystème se situe une société.

| Élément | Règle |
|---|---|
| Nœud central | La société de la fiche |
| Nœuds liés | Fournisseurs, clients, concurrents, partenaires |
| Arêtes | Style selon la relation ; trait plein = fait sourcé ; pointillé = hypothèse |
| Toucher une arête | Ouvre la preuve : document, date, court extrait |
| Toucher un nœud | Mini-fiche ; si l'actif est dans l'univers, accès à sa fiche |
| Nœuds hors univers | Affichés en contexte, grisés, sans métriques |
| Profondeur | 1 niveau par défaut, 2 au maximum |
| Légende | Toujours visible |

Lien avec l'analyse : le graphe alimente le critère `diversification` (deux pistes dépendantes du même fournisseur sont moins diversifiantes qu'il n'y paraît). C'est ce qui en fait un outil d'aide à la décision et pas seulement une illustration.

Technique : `react-native-svg` + simulation de forces (`d3-force`), gestes avec `react-native-gesture-handler`. Repli si le temps manque : disposition radiale fixe.

## Composants

| Composant | Rôle |
|---|---|
| `SimulationBanner` | Bandeau permanent « Simulation — aucune transaction réelle » |
| `MoveCard` | Carte d'une piste |
| `FitBadge` | Adéquation au profil |
| `EvidenceChip` | Pastille de source, ouvre la preuve |
| `ClaimTag` | Étiquette Hypothèse / Scénario |
| `SupplyChainGraph` | Graphe de dépendances |
| `RiskMeter` | Indicateur de risque comparé au profil |
| `DebateSummary` | Trois positions + désaccord |
| `ContributionBars` | Contribution des critères au score |
| `RunProgress` | Étapes de l'analyse en cours |
| `UnknownsBlock` | Bloc « Ce que nous ne savons pas » |
| `SentimentGauge` | Jauge de sentiment (extra) |
| `GlossaryTerm` | Terme expliqué au toucher |

## Rédaction

| À éviter | À utiliser |
|---|---|
| « Achetez », « Vendez », « Vous devriez » | « Piste cohérente avec votre profil », « À examiner » |
| « Meilleur placement » | « Adéquation élevée avec le profil » |
| « Rendement attendu » | « Rendement observé de [date] à [date] » |
| « Recommandation » | « Piste à explorer » |
| « Sans risque », « Garanti » | Ne pas utiliser |

## Accessibilité

- Taille de texte confortable, contraste élevé, zones tactiles larges.
- L'information ne repose jamais sur la couleur seule : icône + libellé.
- Français par défaut, anglais si le temps le permet.

## Pile technique

| Choix | Raison |
|---|---|
| Expo (React Native) + TypeScript | Démarrage rapide, test sur téléphone immédiat, export web pour le jury |
| `expo-router` | Navigation par fichiers |
| TanStack Query | Appels à l'API et interrogation périodique d'un run |
| Zustand | État local léger (profil courant, mode Simple / Avancé) |
| `react-native-svg` | Graphe et graphiques |
| Données simulées dans `src/mocks/` | Le front avance avant le backend |
