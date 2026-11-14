# 0003 — Orchestration par Step Functions, modèles par Bedrock

**État** : proposée (dépend des services ouverts dans le compte AWS du datathon)

## Contexte

AWS est une condition d'admissibilité et pèse 15 %. Le pipeline a une forme fixe : étapes en série, deux branches parallèles, un débat à trois.

## Décision

- Step Functions orchestre le pipeline ; chaque étape est une fonction Lambda.
- Les agents appellent les modèles par Amazon Bedrock, avec sortie structurée.
- L'agent de recherche, seul à choisir ses outils, peut utiliser le SDK Strands Agents.
- Le même code tourne en local par `orchestration/pipeline.py`.

## Alternatives

- Héberger les agents sur Bedrock AgentCore : plus orienté agents, plus d'inconnues en temps limité.
- Tout dans une seule Lambda : plus simple, mais pas de trace visuelle et risque de dépassement de durée.

## Conséquences

- L'historique d'exécution sert de trace observable et de support de démo.
- La structure du flux est figée dans la machine d'états ; la liberté des agents est dans le contenu, pas dans l'enchaînement.
