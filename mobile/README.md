# Application mobile EasyTrade (Expo / React Native)

Conception : `docs/07_UX_UI.md`. État : tous les écrans sont réalisés ; l'application fonctionne sur des données fictives (sans backend) ou branchée sur l'API réelle du dépôt. Restent l'essai sur téléphone et l'API déployée sur AWS (P4).

## Démarrer

Node 20 ou plus récent (testé avec Node 24).

```bash
cd mobile
npm install
npx expo start          # puis : touche w (navigateur), ou scanner le QR code avec Expo Go sur le téléphone
```

| Commande | Rôle |
|---|---|
| `npm run typecheck` | Vérification TypeScript de l'application et des tests |
| `npm test` | Contrat mobile ↔ backend, client HTTP, règles d'affichage (voir « Tests ») |
| `npm run e2e:api` | Parcours complet dans un navigateur, sur l'API réelle (lancée par le script) |
| `npm run e2e:mock` | Même parcours sur les données fictives |
| `npm run contracts` | Régénère `contracts.schema.json` après une modification de `src/types/contracts.ts` |
| `npm run export:web` | Export web statique dans `dist/` (version hébergée pour le jury, extra n° 6) |
| `npx expo-doctor` | Contrôle des versions et de la configuration Expo |

Pile : Expo SDK 58, `expo-router` (navigation par fichiers dans `app/`), TanStack Query (appels et interrogation d'un run), Zustand + AsyncStorage (profil courant, mode Simple / Avancé), `react-native-svg` (graphe).

## Données fictives ou API

| Variable | Défaut | Effet |
|---|---|---|
| `EXPO_PUBLIC_USE_MOCKS` | `true` | `true` : tout est servi par `src/mocks/server.ts`. `false` : appels HTTP. |
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000` | URL de l'API (FastAPI en local, puis API Gateway). |

Les variables se mettent dans `mobile/.env` (non versionné) ou dans l'environnement avant `npx expo start`. Sur un téléphone, `localhost` désigne le téléphone : utiliser l'adresse IP locale de l'ordinateur (`http://192.168.x.x:8000`) ou l'URL API Gateway.

### Brancher l'API réelle

```bash
# Terminal 1 — API (données du dépôt ; agents simulés tant que Bedrock n'est pas configuré)
cd backend && uvicorn easytrade.api.app:app --port 8000        # ajouter --host 0.0.0.0 pour un téléphone

# Terminal 2 — application
cd mobile && EXPO_PUBLIC_USE_MOCKS=false npx expo start
# PowerShell : $env:EXPO_PUBLIC_USE_MOCKS="false"; npx expo start
```

Le bandeau « Données entièrement fictives » disparaît : les pistes, les chiffres et les preuves viennent du pipeline (`backend/easytrade/orchestration/pipeline.py`) sur les 31 actifs du jeu de départ.

À savoir :

- **Les preuves sont propres à une analyse.** `EV-000412` ne désigne pas la même preuve dans deux runs : la preuve, la fiche et le graphe sont demandés avec le `run_id` consulté (`src/api/assets.ts`).
- **Même demande, même analyse.** L'identifiant d'un run est déterministe ; « Relancer l'analyse » rend le même résultat tant que les données n'ont pas changé.
- **Runs et profils fictifs sont en mémoire de l'API.** Après un redémarrage de l'API, l'application relance l'analyse ; un profil créé par questionnaire est à recréer (« Changer de profil »).
- **Le graphe est vide** tant que `data/reference/graph_edges.csv` n'est pas rempli (bloc G) : la fiche affiche « Aucune relation sourcée ».
- **Mateo obtient « aucune recommandation »** tant que les signaux ESG ne sont pas sourcés : c'est la réponse attendue, pas une erreur.

En mode fictif, un second bandeau « Données entièrement fictives » s'affiche sous le bandeau de simulation. **Aucun chiffre de ce mode ne doit apparaître dans la vidéo ou la documentation** : ce sont des valeurs inventées (actifs `ACTIF_A`, `FNB_B`…).

### Le serveur fictif

`src/mocks/server.ts` imite toutes les routes. Il reproduit la *forme* du moteur de décision (contraintes dures → score pondéré `Σ w_k·s_k` → garde-fous de concentration → « aucune recommandation » → cohérence d'une demande) pour que l'interface se comporte comme avec le vrai backend : Robert qui teste `ACTIF_G` obtient « Incohérent avec le profil ». Ses réponses respectent le même schéma que l'API réelle, ses étapes de trace portent les mêmes noms, et il refuse les mêmes choix de questionnaire. **Ce n'est pas le moteur** : la référence est `backend/easytrade/engine/`.

Les personas viennent du vrai `data/reference/personas.json` (importé grâce à `metro.config.js`). La liste des sources de l'écran Données recopie `data/reference/sources_registry.csv`. Tout le reste est fictif.

## Écrans

| Route | Écran | Tâche `avancement.md` |
|---|---|---|
| `app/index.tsx` | Entrée : profil au premier lancement, sinon pistes | F1 |
| `app/onboarding/index.tsx` | Bienvenue, 3 personas, « Créer un profil fictif » | F3 |
| `app/onboarding/questionnaire.tsx` | 5 questions, une par écran ; baisse simulée illustrée | F3 |
| `app/onboarding/resume.tsx` | « Voici comment nous avons compris votre profil » : règles, poids modifiables, justifications | F3 |
| `app/(tabs)/index.tsx` | Pistes à explorer : progression, cartes, écartées, « Aucune recommandation », bouton « Tester une idée » | F4 |
| `app/piste/[ticker].tsx` | Fiche : aperçu, graphe, risque, débat, signaux, contributions, inconnues | F5, F8 |
| `app/preuve/[id].tsx` | « Pourquoi ? » : preuve (source, trois dates, traitement, limites, étiquette) | F6 |
| `app/run/[id].tsx` | Parcours de l'analyse : étapes, durées, modèles, contrôles de gouvernance | F6 |
| `app/(tabs)/tester.tsx` | Tester une idée : verdict, tensions chiffrées, panier simulé, alternatives | F7 |
| `app/(tabs)/profil.tsx` | Profil courant, mode Simple / Avancé, changement de profil | F3 |
| `app/comparer.tsx` | Deux profils côte à côte, différences surlignées (extra n° 2) | — |
| `app/donnees.tsx` | Sources, contrôles qualité, chronologie des preuves (point-in-time) | — |

`SentimentGauge` (extra n° 8) reste un squelette. Le graphe est la version radiale fixe ; la version à simulation de forces est l'extra n° 7.

## Contrats

`src/types/contracts.ts` décrit tout ce que l'API renvoie à l'application. Le backend s'y conforme : `Explanation`, `Trace` et `Evidence` sont les schémas du pipeline, et `backend/easytrade/api/service.py` traduit le reste (`ProfileWeights`, `RunStatus`, `AssetSheet`, `DependencyGraph`, `DataOverview`) depuis les schémas internes du moteur.

`contracts.schema.json` est le schéma JSON de ces types, généré par `npm run contracts`. C'est la référence commune : les tests du mobile et ceux du backend valident contre ce même fichier.

**Changer un champ** : modifier `contracts.ts` et le schéma Pydantic correspondant (`backend/easytrade/schemas/`), lancer `npm run contracts`, puis `npm test` ici et `pytest tests/api` dans `backend/`. Un changement fait d'un seul côté fait échouer l'un des deux.

Routes : table de `docs/01_ARCHITECTURE.md`. Exemples JSON conformes : `src/mocks/explanation.exemple.json` (run fictif d'Amira), `evidence.exemple.json`, `graph.exemple.json`.

## Tests

| Fichier | Ce qui est vérifié |
|---|---|
| `tests/contracts.test.ts` | `contracts.schema.json` est à jour ; chaque route du serveur fictif respecte le schéma ; aucune formulation de `data/reference/forbidden_wording.txt` ; toute preuve citée existe et n'est pas postérieure à l'analyse ; toute arête du graphe a une preuve ou l'étiquette Hypothèse ; le validateur refuse bien un écart |
| `tests/client.test.ts` | URL appelées en mode API, `run_id` transmis pour la preuve, la fiche, le graphe et les données, corps de `POST /runs` et `POST /profiles`, erreurs 404 et API injoignable |
| `e2e/run.mjs` | Parcours complet avec clics réels dans Chrome : exporte la version web, la sert, lance l'API (`--api`), puis échoue sur toute attente non satisfaite, erreur de console ou réponse HTTP en erreur. `E2E_SHOTS=<dossier>` enregistre une capture par étape |
| `backend/tests/api/` (dans le backend) | L'API réelle respecte le même schéma, route par route |

Prérequis de `e2e` : Chrome ou Edge (`CHROME_PATH` pour un autre emplacement) ; pour `e2e:api`, l'environnement Python du backend (`EASYTRADE_PYTHON`, sinon `backend/.venv`, sinon `python`).

## Structure

| Dossier | Rôle |
|---|---|
| `app/` | Écrans (un fichier = une route) |
| `src/components/` | Composants d'interface (`ui.tsx` : briques communes) |
| `src/api/` | Appels à l'API, bascule fictif / réel (`client.ts`) |
| `src/hooks/` | `useBaseRun` : lance ou reprend l'analyse de base d'un profil |
| `src/types/` | Types des contrats JSON |
| `src/store/` | État local persisté |
| `src/theme/` | Couleurs, espacements, typographie |
| `src/i18n/` | Textes et glossaire |
| `src/mocks/` | Serveur et données fictives |
| `src/format.ts` | Nombres, pourcentages et dates en français |
| `tests/`, `e2e/`, `scripts/` | Tests du contrat et du client, parcours de bout en bout, génération du schéma |

## Règles d'interface appliquées

- Bandeau « Simulation — aucune transaction réelle » sur tous les écrans (mise en page racine).
- Aucune affirmation sans pastille de source ; étiquettes Hypothèse / Scénario fictif visibles sans action.
- Couleur jamais seule : chaque état porte une icône et un libellé (adéquation, confiance, verdict, débat).
- Zones tactiles d'au moins 44 px ; texte de 16 px par défaut.
- Vocabulaire non prescriptif (`docs/07_UX_UI.md`, section Rédaction) ; vérifié sur toutes les sorties fictives avec `data/reference/forbidden_wording.txt`.
