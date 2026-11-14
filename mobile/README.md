# Application mobile EasyTrade (Expo / React Native)

Conception : `docs/07_UX_UI.md`. État : phase P5 réalisée sur données fictives ; branchement à l'API réelle en attente du backend (P2 à P4).

## Démarrer

Node 20 ou plus récent (testé avec Node 24).

```bash
cd mobile
npm install
npx expo start          # puis : touche w (navigateur), ou scanner le QR code avec Expo Go sur le téléphone
```

| Commande | Rôle |
|---|---|
| `npm run typecheck` | Vérification TypeScript (`tsc --noEmit`) |
| `npm run export:web` | Export web statique dans `dist/` (version hébergée pour le jury, extra n° 6) |
| `npx expo-doctor` | Contrôle des versions et de la configuration Expo |

Pile : Expo SDK 58, `expo-router` (navigation par fichiers dans `app/`), TanStack Query (appels et interrogation d'un run), Zustand + AsyncStorage (profil courant, mode Simple / Avancé), `react-native-svg` (graphe).

## Données fictives ou API

| Variable | Défaut | Effet |
|---|---|---|
| `EXPO_PUBLIC_USE_MOCKS` | `true` | `true` : tout est servi par `src/mocks/server.ts`. `false` : appels HTTP. |
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000` | URL de l'API (FastAPI en local, puis API Gateway). |

Les variables se mettent dans `mobile/.env` (non versionné) ou dans l'environnement avant `npx expo start`. Sur un téléphone, `localhost` désigne le téléphone : utiliser l'adresse IP locale de l'ordinateur (`http://192.168.x.x:8000`) ou l'URL API Gateway.

En mode fictif, un second bandeau « Données entièrement fictives » s'affiche sous le bandeau de simulation. **Aucun chiffre de ce mode ne doit apparaître dans la vidéo ou la documentation** : ce sont des valeurs inventées (actifs `ACTIF_A`, `FNB_B`…).

### Le serveur fictif

`src/mocks/server.ts` imite toutes les routes. Il reproduit la *forme* du moteur de décision (contraintes dures → score pondéré `Σ w_k·s_k` → garde-fous de concentration → « aucune recommandation » → cohérence d'une demande) pour que l'interface se comporte comme avec le vrai backend : un profil fictif qui exclut tout donne bien « Aucune piste », Robert qui teste `ACTIF_G` obtient « Incohérent avec le profil ». **Ce n'est pas le moteur** : la référence sera `backend/easytrade/engine/` (P2).

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

`src/types/contracts.ts` est le miroir TypeScript des schémas Pydantic. `Evidence` reprend exactement `backend/easytrade/schemas/evidence.py`. Pour le reste, les schémas backend (P2, P3) ne sont pas encore écrits : le front **propose** ces champs, à reprendre côté Pydantic ou à aligner.

| Contrat | Champs proposés par le front |
|---|---|
| `ProfileWeights` | `label`, `summary` (affichage) |
| `ProfileDraft` (corps de `POST /profiles`) | `objectif`, `horizon`, `tolerance`, `preferences`, `exclusions`, `weights_override`, `base_persona` |
| `RunStatus` (`GET /runs/{id}`) | `status`, `steps[{id, status}]` avec `id ∈ profil, recherche_validation, debat, decision, explication`, `result` |
| `Explanation` | `no_recommendation`, `missing`, `coherence` (analyse de « Tester une idée »), `unknowns` |
| `ExplanationItem` | `sector`, `to_review`, `debate` (positions complètes du tour 3), `contributions`, `unknowns` |
| `RejectedItem` | `kind ∈ contrainte, classement, preuves` (« écarté par une règle » contre « moins bien classé »), `evidence_ids` |
| `AssetSheet` (`GET /assets/{ticker}?profile_id=`) | `metrics[]` avec `universe_min`, `universe_max`, `profile_limit` (seuil indicatif du profil, hypothèse), `advanced` ; `signals[]` |
| `TraceStep` | `kind ∈ code, llm, controle`, `note` (résultat d'un contrôle) |

Les schémas internes du moteur (P2 : `Decision`, `ScoredCandidate`, `Rejection`, `CoherenceReport`, `ProfileWeights`) ne correspondent pas encore à ces contrats de réponse ; les écarts sont listés dans `avancement.md` (étape 5) et sont à résoudre en F9, de préférence dans la couche API ou l'agent d'explication.

Routes ajoutées à la table de `docs/01_ARCHITECTURE.md` : `GET /profiles/{id}`, `GET /assets` (univers), `GET /data` (sources + contrôles qualité).

Exemples JSON conformes, générés depuis le serveur fictif : `src/mocks/explanation.exemple.json` (run d'Amira), `evidence.exemple.json`, `graph.exemple.json`.

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

## Règles d'interface appliquées

- Bandeau « Simulation — aucune transaction réelle » sur tous les écrans (mise en page racine).
- Aucune affirmation sans pastille de source ; étiquettes Hypothèse / Scénario fictif visibles sans action.
- Couleur jamais seule : chaque état porte une icône et un libellé (adéquation, confiance, verdict, débat).
- Zones tactiles d'au moins 44 px ; texte de 16 px par défaut.
- Vocabulaire non prescriptif (`docs/07_UX_UI.md`, section Rédaction) ; vérifié sur toutes les sorties fictives avec `data/reference/forbidden_wording.txt`.
