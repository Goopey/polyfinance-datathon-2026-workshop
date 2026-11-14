# 09 — Scénarios de test

Ces scénarios sont la définition de « ça marche ». Leur état est suivi dans `avancement.md` (passe / échoue, avec l'écart constaté).

Convention : chaque scénario a un test automatisé dans `backend/tests/scenarios/` et, quand c'est pertinent, une vérification à l'écran.

## Scénarios personas (tests de réalité du case)

### S1 — Amira : le risque élevé garde une diversification

- **Donné** : profil `amira`, `as_of = 2026-11-12`.
- **Attendu** :
  1. Des pistes technologiques ou crypto apparaissent (le profil offensif est respecté).
  2. Les plafonds sont tenus : part crypto, part par secteur, part par actif.
  3. Au moins trois secteurs ou classes d'actifs hors technologies dans les pistes retenues.
  4. L'explication cite le souhait de diversification comme origine de la règle.
  5. Au moins un candidat est écarté ou déclassé pour concentration, avec le motif.
- **Échec type** : liste composée uniquement de titres technologiques et de crypto.

### S2 — Mateo : l'ESG change le résultat

- **Donné** : profil `mateo`.
- **Attendu** :
  1. Tout titre porteur d'une controverse documentée est écarté, preuve citée.
  2. Aucune piste crypto.
  3. Avec le poids `esg` mis à zéro, le classement diffère : la différence est affichable.
  4. Un actif sans donnée ESG est marqué « information manquante », pas traité comme conforme.
  5. Une technologie émergente peut apparaître si son risque est compatible, avec justification.
- **Échec type** : même classement qu'un profil modéré sans préférence ESG.

### S3 — Robert : la demande incohérente est remise en question

- **Donné** : profil `robert`, `requested_ticker` = un titre très médiatisé et volatil de l'univers.
- **Attendu** :
  1. Le titre est analysé, pas ignoré.
  2. Verdict différent de « cohérent » ; tensions chiffrées (volatilité, perte maximale, horizon de 3 à 5 ans).
  3. L'effet sur le panier simulé est montré.
  4. Pas d'acquiescement automatique ni de refus sec : explication du risque et mise en contexte.
  5. Les pistes par défaut de Robert privilégient des actifs établis, sans crypto.
- **Échec type** : le titre apparaît dans les pistes sans réserve, ou disparaît sans explication.

## Scénarios transverses

### S4 — « Aucune recommandation »

- **Donné** : un profil dont les contraintes écartent tous les candidats, ou des métriques rendues indisponibles.
- **Attendu** : sortie « aucune recommandation », avec ce qui manque. Aucune piste forcée.

### S5 — Aucune fuite du futur

- **Donné** : `as_of` fixé à une date passée (ex. 2024-06-28).
- **Attendu** :
  1. Aucune preuve du run n'a `published_at > as_of`.
  2. Une donnée macro mensuelle non encore publiée à cette date n'est pas utilisée.
  3. Les métriques ne changent pas si l'on ajoute des données postérieures à `as_of`.

### S6 — Fidélité de l'explication

- **Attendu** :
  1. Chaque nombre du texte correspond à une preuve citée.
  2. Chaque affirmation a au moins un `evidence_id` valide.
  3. Taux de réussite du vérificateur mesuré sur les runs des trois personas et rapporté.

### S7 — Comparabilité

- **Attendu** :
  1. Les agrégations sont en CAD ; un actif en USD est converti au taux du jour, dernier taux connu les jours fériés.
  2. Les rendements utilisent `adj_close`.
  3. Les fractionnements ne sont pas appliqués une seconde fois.
  4. Crypto et actions sont annualisées selon leur calendrier.

### S8 — Formulation et cadre de simulation

- **Attendu** :
  1. Aucun terme de la liste interdite dans les sorties (achetez, vendez, vous devriez, garanti, sans risque, rendement attendu).
  2. La mention de simulation est présente dans chaque `Explanation`.
  3. Aucune route de l'API ne permet de passer un ordre.

### S9 — Exactitude et déterminisme des calculs

- **Attendu** :
  1. Deux exécutions de la couche de validation sur les mêmes données donnent des résultats identiques.
  2. Rendement, volatilité et perte maximale d'un actif témoin recoupés par un calcul indépendant.

### S10 — Graphe sourcé

- **Attendu** : chaque arête affichée porte un document daté, ou l'étiquette « Hypothèse ». Aucune arête sans l'un des deux.

### S11 — Désaccord conservé

- **Donné** : un candidat sur lequel les positions finales divergent.
- **Attendu** : le désaccord figure dans `Decision.disagreements` et dans l'explication ; la confiance n'est pas « élevée ».

### S12 — Adaptation au profil

- **Donné** : même univers et même date pour Amira et Robert.
- **Attendu** : classements différents ; chaque différence s'explique par un poids ou une contrainte nommée.

## Tableau de suivi (recopié dans `avancement.md`)

| ID | Scénario | Automatisé | État |
|---|---|:-:|---|
| S1 | Amira : diversification | — | Non exécuté |
| S2 | Mateo : ESG | — | Non exécuté |
| S3 | Robert : demande incohérente | — | Non exécuté |
| S4 | Aucune recommandation | — | Non exécuté |
| S5 | Aucune fuite du futur | — | Non exécuté |
| S6 | Fidélité de l'explication | — | Non exécuté |
| S7 | Comparabilité | — | Non exécuté |
| S8 | Formulation et simulation | — | Non exécuté |
| S9 | Exactitude et déterminisme | — | Non exécuté |
| S10 | Graphe sourcé | — | Non exécuté |
| S11 | Désaccord conservé | — | Non exécuté |
| S12 | Adaptation au profil | — | Non exécuté |
