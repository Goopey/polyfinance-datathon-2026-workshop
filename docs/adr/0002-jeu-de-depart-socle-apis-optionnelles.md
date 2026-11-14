# 0002 — Jeu de départ comme socle, APIs tierces optionnelles

**État** : proposée (à valider en équipe)

## Contexte

Le brief envisage Alpaca et Finnhub. Le case demande de respecter les conditions d'accès, de conservation et de redistribution, et de documenter chaque source. Le jeu de départ fournit déjà 5 ans de prix, le change et la macro, avec sources et limites documentées.

## Décision

- Le socle est le jeu de départ, complété par des sources publiques citées par le case (SEC EDGAR, SEDAR+, Banque du Canada, FRED, émetteurs de FNB).
- Alpaca et Finnhub restent des adaptateurs optionnels, désactivés par défaut, activables après vérification de leurs conditions.
- Jamais d'appel à une API d'ordres.

## Alternatives

- Tout brancher sur des APIs temps réel : démo plus vivante, mais risque de licence et dépendance au réseau pendant la vidéo.

## Conséquences

- Le prototype fonctionne hors ligne sur des données datées, ce qui rend la vidéo reproductible.
- Le « temps réel » n'est pas un argument du pitch ; la traçabilité l'est.
