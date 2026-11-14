# Application mobile EasyTrade (Expo / React Native)

Conception : `docs/07_UX_UI.md`.

## Initialisation (première tâche de la phase Mobile)

Ce dossier contient la structure des écrans et des composants, pas encore le projet Expo lui-même.

1. Générer un projet Expo TypeScript vide dans un dossier temporaire (`npx create-expo-app`).
2. Copier ici ses fichiers de configuration (`package.json`, `app.json`, `tsconfig.json`, `babel.config.js` s'il existe).
3. Installer : navigation par fichiers (`expo-router`), `react-native-svg`, `@tanstack/react-query`, `zustand`, `d3-force`, `react-native-gesture-handler`.
4. `npx expo start`.

## Structure

| Dossier | Rôle |
|---|---|
| `app/` | Écrans (un fichier = une route) |
| `src/components/` | Composants d'interface |
| `src/api/` | Appels à l'API |
| `src/types/` | Types des contrats JSON (miroir de `backend/easytrade/schemas/`) |
| `src/store/` | État local |
| `src/theme/` | Couleurs, espacements, typographie |
| `src/i18n/` | Textes et glossaire |
| `src/mocks/` | Données fictives conformes aux contrats, pour avancer sans backend |

`EXPO_PUBLIC_USE_MOCKS=true` fait lire `src/mocks/` au lieu de l'API.
