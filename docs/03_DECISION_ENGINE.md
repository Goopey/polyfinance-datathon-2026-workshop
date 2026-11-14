# 03 — Moteur de décision

Le profil choisi dicte la pondération du moteur. Le moteur est du Python déterministe : mêmes entrées, même sortie.

## Étapes

```
ProfileWeights + MetricsTable + DebateRecord[]
   1. Contraintes dures      → candidats admissibles / rejetés (avec motif)
   2. Scores par critère     → valeurs entre 0 et 1, issues des métriques
   3. Score d'adéquation     → somme pondérée par les poids du profil
   4. Prise en compte du débat → niveau de confiance + désaccords conservés
   5. Garde-fous de panier   → diversification, plafonds
   6. Sortie                 → classement, rejets, tensions, ou « aucune recommandation »
```

## Critères

| Critère | Ce qu'il mesure | Preuves utilisées |
|---|---|---|
| `croissance` | Profil de croissance observé (rendement annualisé sur fenêtre explicite ; croissance des revenus si disponible) | Prix ajustés, dépôts |
| `stabilite` | Volatilité, perte maximale, comportement en 2022 | Prix ajustés |
| `diversification` | Apport au panier simulé : corrélation, concentration par secteur et classe d'actifs | Prix, univers |
| `esg` | Signaux ESG documentés et controverses datées | Sources ESG citées |
| `qualite` | Solidité : rentabilité, endettement ; pour un FNB : frais, diversification interne | Dépôts, fiches d'émetteurs |
| `horizon` | Pire période glissante de durée égale à l'horizon | Prix ajustés |
| `preferences` | Correspondance avec les préférences déclarées (thèmes, types d'actifs) | Univers, profil |

Limites à afficher :

- `croissance` et `horizon` décrivent le passé sur 5 ans. Ils ne prédisent rien et ne couvrent pas un horizon de 15 ans.
- `esg` peut valoir « inconnu ». Un inconnu n'est jamais traité comme un bon score : il baisse la confiance et s'affiche comme information manquante.

## Poids de départ par persona

Hypothèses de travail à calibrer avec les scénarios de `09_SCENARIOS_TEST.md`. La somme de chaque ligne vaut 1. Source unique : `data/reference/personas.json`.

| Critère | Amira | Mateo | Robert |
|---|---:|---:|---:|
| croissance | 0,30 | 0,15 | 0,10 |
| stabilite | 0,10 | 0,20 | 0,30 |
| diversification | 0,20 | 0,15 | 0,15 |
| esg | 0,05 | 0,25 | 0,05 |
| qualite | 0,10 | 0,15 | 0,25 |
| horizon | 0,10 | 0,05 | 0,10 |
| preferences | 0,15 | 0,05 | 0,05 |

## Contraintes dures de départ

| Contrainte | Amira | Mateo | Robert |
|---|---|---|---|
| Part maximale par actif | 15 % | 10 % | 10 % |
| Part maximale par secteur | 40 % | 30 % | 30 % |
| Part maximale en crypto | 15 % | 0 % | 0 % |
| Exclusion sur controverse documentée | non | oui | non |
| Actifs « hautement spéculatifs » | permis | exclus | signalés |

Une contrainte dure **écarte** ; un poids **classe**. La différence est montrée à l'utilisateur : « écarté par une règle de votre profil » contre « moins bien classé ».

## Score d'adéquation

```
score(a) = Σ_k  w_k · s_k(a)        avec Σ w_k = 1 et s_k(a) ∈ [0, 1]
```

- `s_k` est normalisé dans l'univers à la date `as_of` (rang centile), ce qui évite de comparer des unités différentes.
- La contribution de chaque critère (`w_k · s_k`) est conservée : c'est elle qui alimente le graphique « pourquoi ce classement » dans l'application.

## Rôle du débat

Le débat ne modifie pas le score. Il produit :

- un **niveau de confiance** (élevé / moyen / faible) selon l'accord des trois positions finales ;
- des **désaccords** recopiés tels quels dans la sortie ;
- des **questions ouvertes** (preuves manquantes).

Règle : une opposition du Bear appuyée sur un fait lié à une contrainte du profil déclenche un drapeau « à examiner » sur le candidat.

## Demande explicite de l'utilisateur (« Tester une idée »)

Quand l'utilisateur soumet un titre, le moteur ne filtre pas en silence. Il produit une **analyse de cohérence** :

| Sortie | Contenu |
|---|---|
| `tensions[]` | Chaque écart entre le titre et le profil, chiffré (ex. volatilité du titre comparée à celle des pistes retenues, horizon court) |
| `verdict` | `cohérent`, `cohérent avec réserve`, `incohérent avec le profil` |
| `context` | Ce que le titre changerait dans le panier simulé (concentration, volatilité globale) |
| `alternatives` | Actifs de l'univers qui répondent au même intérêt avec moins de tension, si la preuve existe |

C'est la réponse au test Robert : relever la tension, expliquer le risque, ne pas acquiescer automatiquement.

## « Aucune recommandation »

Sortie valide et attendue dans ces cas :

- aucun candidat ne passe les contraintes dures ;
- preuves insuffisantes (métriques manquantes, fenêtre trop courte) ;
- confiance faible sur tous les candidats.

Le résultat explique alors ce qui manque.

## Sensibilité

Pour « mettre les résultats à l'épreuve » :

- **Changer un poids** : recalculer le classement avec ±0,10 sur un critère ; afficher les pistes qui changent de rang.
- **Changer de profil** : même univers, autre persona ; afficher les différences côte à côte.
- **Changer la fenêtre** : 5 ans, 3 ans, sans 2022.

Un classement qui bascule au moindre changement est signalé comme fragile.

## Garde-fous de panier

Si l'application présente un panier simulé :

- plafonds de `hard_constraints` appliqués après le classement ;
- au moins trois classes d'actifs ou secteurs distincts pour un profil qui demande de la diversification ;
- conversion en CAD pour toute agrégation (voir `04_DONNEES.md`).
