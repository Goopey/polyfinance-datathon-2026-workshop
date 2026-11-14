# 00 — Vision et cadrage

## North star

> **EasyTrade** : une application agentique, intuitive, qui s'appuie sur des données publiques vérifiables pour rendre une décision d'investissement **claire, contextualisée et explicable** — en simulation uniquement.

## La question d'investissement que l'on traite

Le case demande de partir d'une question, pas de la technologie. La nôtre :

> **« Parmi les actifs que je peux examiner, lesquels méritent mon attention *compte tenu de mon profil*, et pourquoi — et quand une idée qui me tente est-elle incohérente avec ce profil ? »**

Cette question couvre les trois tests de réalité :

| Persona | Ce que la question force à démontrer |
|---|---|
| Amira | Un profil offensif garde une logique de diversification (« risque élevé » ≠ « tout est acceptable »). |
| Mateo | Des critères non financiers (ESG, controverses) changent réellement le classement. |
| Robert | Une demande incohérente avec le profil est relevée, chiffrée et remise en contexte, pas approuvée par défaut. |

## Ce que fait l'application (cas d'usage complet)

1. **Profil** — au premier lancement, l'utilisateur choisit un persona ou compose un profil fictif (objectif, tolérance au risque, horizon, contraintes, préférences).
2. **Pistes à explorer** — l'écran d'accueil présente des pistes classées selon leur adéquation au profil, chacune avec une explication courte et sourcée.
3. **Fiche d'une piste** — le graphe de dépendances (fonctionnalité phare), puis en défilant : indicateurs de risque, synthèse du débat Bull/Réaliste/Bear, signaux (ESG, nouvelles), limites.
4. **Tester une idée** — l'utilisateur soumet un titre de son choix ; le système dit s'il est cohérent avec le profil et pourquoi (test Robert).
5. **Pourquoi ?** — depuis n'importe quel chiffre ou affirmation, accès à la preuve (source, date, traitement) et à la trace d'exécution.

## Exigences de l'équipe → décisions de conception

| Exigence | Décision | Document |
|---|---|---|
| Adaptable à tous les profils | Le profil produit des **contraintes dures** + des **poids** ; le même moteur donne des sorties différentes | `03_DECISION_ENGINE.md` |
| UI intuitive (« même une grand-mère ») | Un écran = une idée ; mode Simple par défaut, mode Avancé sur demande ; vocabulaire sans jargon | `07_UX_UI.md` |
| Data-backed | Aucun chiffre affiché sans entrée dans le registre de preuves | `05_EXPLICABILITE.md` |
| Conforme au datathon | Simulation, vocabulaire non prescriptif, licences documentées | `08_CONFORMITE.md` |

## Alignement sur la grille

| Critère | Poids | Ce qui rapporte les points chez nous |
|---|---|---|
| Solution (pertinence, innovation, prototype) | 20 % | Graphe de dépendances sourcé ; « Tester une idée » ; possibilité de « aucune recommandation » |
| Intelligence agentique et explicabilité | 20 % | Conseil de débat à dissidence préservée ; **les LLM argumentent, le code décide** ; registre de preuves + trace |
| Données (rigueur, validation, visualisation) | 20 % | Point-in-time strict, couche de validation déterministe, contrôles qualité, sensibilité |
| UX/UI | 10 % | Parcours en 3 écrans, graphe interactif, « Pourquoi ? » partout |
| AWS (admissibilité + 15 %) | 15 % | Step Functions = le diagramme agentique visible ; Bedrock ; chaque service a un rôle montré en démo |
| Pitch, business, marketing | 15 % | Histoire unique : « de la complexité à la clarté », deux personas contrastés |

## Principes directeurs

1. **Les LLM argumentent, le code décide.** Calculs et décision finale sont déterministes et rejouables.
2. **Pas de preuve, pas d'affirmation.** Chaque chiffre et chaque affirmation pointe vers une preuve datée.
3. **Fait / Hypothèse / Scénario** toujours distingués, à l'écran comme dans les données.
4. **Le système sait dire « je ne sais pas ».** « Aucune recommandation » est une sortie valide.
5. **MVP d'abord.** Un parcours complet sur 2 personas avant tout extra.

## Hors périmètre

- Aucune exécution d'ordre, aucun compte de courtage, aucune donnée bancaire ou personnelle réelle.
- Aucune prévision de rendement ni de prix cible.
- Produits dérivés, marge, vente à découvert.

## Point d'attention sur le vocabulaire (à trancher en équipe)

Le brief interne parle de « next-trade counselor » et de « best moves ». Le case interdit de se présenter comme un conseil financier personnalisé. Dans le produit, on utilise donc :

| Brief interne | Dans l'application |
|---|---|
| best moves | **pistes à explorer** (simulation) |
| next-trade counselor | **assistant d'aide à la décision** |
| move sélectionné | **fiche de la piste** |
| recommandation | **adéquation au profil** (élevée / partielle / faible) |

Le nom « EasyTrade » évoque la transaction. Si on le garde, le sous-titre et un bandeau permanent doivent lever l'ambiguïté : « Simulateur d'aide à la décision — aucune transaction réelle ». Voir `08_CONFORMITE.md`.
