# 0001 — Les LLM argumentent, le code décide

**État** : acceptée

## Contexte

Le case exige des explications fidèles aux données et aux actions observables, sans justification inventée. Un classement produit par un modèle de langage ne se rejoue pas à l'identique et ne se vérifie pas.

## Décision

- Les calculs financiers et la décision finale sont du Python déterministe.
- Les modèles interprètent le profil, choisissent les données à mobiliser, argumentent et rédigent.
- Aucun modèle ne produit de chiffre ; ils citent des identifiants de preuves.

## Alternatives

- Tout confier à un agent unique : plus rapide, mais invérifiable.
- Aucun modèle dans la décision ni l'argumentation : vérifiable, mais plus d'approche agentique.

## Conséquences

- Les scénarios S4, S9, S12 se testent sans appel à un modèle.
- Il faut un contrat strict entre agents et moteur (`schemas/`).
