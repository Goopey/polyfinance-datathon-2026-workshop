# 0004 — Expo (React Native) avec export web

**État** : proposée

## Contexte

L'équipe vise une application mobile en React Native. Le jury doit pouvoir voir la solution en action ; la vidéo est le support principal.

## Décision

- Expo et TypeScript, navigation par fichiers.
- Données fictives conformes aux contrats dès le départ.
- Export web hébergé sur AWS si le temps le permet, pour un lien testable.

## Alternatives

- Application web seule : plus rapide, moins conforme à la vision mobile.
- React Native sans Expo : plus de configuration, aucun gain pour un prototype.

## Conséquences

- Le graphe doit fonctionner avec `react-native-svg` sur mobile et sur le web.
