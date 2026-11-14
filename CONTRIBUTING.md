# Travailler dans ce dépôt

## Branches

- `main` : toujours démontrable.
- Une branche par tâche : `data/…`, `engine/…`, `agents/…`, `aws/…`, `mobile/…`, `docs/…`.
- Fusion par demande de tirage courte, relue par une autre personne quand c'est possible.

## Règles non négociables

1. **Aucun accès direct aux fichiers de données** hors de `easytrade/data/`. Tout passe par le filtre point-in-time.
2. **Aucun chiffre produit par un LLM.** Les chiffres viennent de `easytrade/validation/`.
3. **Toute nouvelle source** a sa ligne dans `data/reference/sources_registry.csv` avant d'être utilisée.
4. **Aucune clé** dans le dépôt.
5. **Vocabulaire** : voir la table de rédaction dans `docs/07_UX_UI.md`.

## Après chaque étape terminée

Mettre à jour `avancement.md` : fichiers touchés, scénarios (passe / échoue + écart), tâches restantes.

## Commandes

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                       # tous les tests
pytest tests/scenarios -rs   # scénarios S1 à S12

# Mobile
cd mobile && npm install && npx expo start
```
