# 10 — Plan de réalisation

Les dates limites ne sont pas encore connues (consignes logistiques officielles à venir). Le plan est donc en **phases** avec une part du temps total. À convertir en dates dès que l'échéance est fixée.

## Règle de priorité

1. Un parcours complet et démontrable sur **deux personas contrastés** (Amira et Robert).
2. Puis Mateo (ESG).
3. Puis les extras, dans l'ordre du tableau plus bas.

Un extra ne commence pas tant que les scénarios S1, S3, S5, S6 ne passent pas.

## Phases

| Phase | Part du temps | Contenu | Sortie vérifiable |
|---|---:|---|---|
| P0 Cadrage | fait | Arborescence, conception, scénarios | Ce dépôt |
| P1 Socle données | 15 % | Chargement du jeu de départ, calendrier, change, point-in-time, métriques déterministes, contrôles qualité | S7, S9 passent |
| P2 Moteur | 15 % | Schémas, personas, contraintes, score, « aucune recommandation », cohérence d'une demande | S4, S12 passent sans LLM |
| P3 Agents | 20 % | Client Bedrock, pondération, recherche, débat (tours 1 et 3), explication, vérificateur de fidélité | S1, S3, S6 passent en local |
| P4 AWS | 15 % | CDK : S3, DynamoDB, Lambda, Step Functions, API Gateway ; déploiement | Un run complet sur AWS, trace visible |
| P5 Mobile | 20 % | Profil, pistes, fiche, « Pourquoi ? », « Tester une idée », graphe | Parcours complet sur téléphone avec l'API réelle |
| P6 Mateo + extras | 5 % | Données ESG, S2 ; extras selon le temps | S2 passe |
| P7 Livrables | 10 % | Vidéo, documentation technique, one-pager, README, répétition du pitch | Les quatre livrables prêts |

P1 + P2 et P5 (avec données simulées) démarrent en parallèle. P4 démarre dès que le compte AWS est disponible, sans attendre P3.
## Répartition proposée

À adapter au nombre de personnes et aux affinités.

| Rôle | Périmètre | Phases |
|---|---|---|
| Données | Ingestion, point-in-time, métriques, qualité, ESG, arêtes du graphe | P1, P6 |
| Agents et moteur | Schémas, moteur, prompts, débat, explication, fidélité | P2, P3 |
| AWS | CDK, Step Functions, déploiement, observabilité, sécurité | P4 |
| Mobile et design | Expo, écrans, graphe, composants | P5 |
| Pitch (rôle partagé) | Scénario de la vidéo, one-pager, documentation | P7, en continu |

## MVP et extras

| Fonctionnalité | Critère amélioré | Coût | Niveau |
|---|---|---|---|
| Pipeline complet sur 2 personas | Solution, Agentique | Élevé | MVP |
| Registre de preuves + « Pourquoi ? » | Agentique, Données | Moyen | MVP |
| Vérificateur de fidélité | Agentique | Faible | MVP |
| « Tester une idée » (test Robert) | Solution, Agentique | Moyen | MVP |
| Step Functions + Bedrock + S3 + DynamoDB + API Gateway | AWS (admissibilité) | Élevé | MVP |
| Graphe de dépendances sur 5 à 8 sociétés | Solution, UX, Pitch | Élevé | MVP (version radiale) |
| Mateo et ESG documenté | Solution, Données | Moyen | Extra 1 |
| Comparaison de deux profils côte à côte | Pitch, Agentique | Faible | Extra 2 |
| Sensibilité (poids ±0,10) | Données | Faible | Extra 3 |
| Bedrock Guardrails | AWS, Agentique | Faible | Extra 4 |
| Tour 2 du débat (contre-examen) | Agentique | Moyen | Extra 5 |
| Version web hébergée pour le jury | AWS, Pitch | Faible à moyen | Extra 6 |
| Graphe à simulation de forces, animé | UX | Moyen | Extra 7 |
| Jauge de sentiment | Solution | Moyen à élevé | Extra 8 |
| Knowledge Bases, Athena | AWS | Moyen | Extra 9 |

## Définition de « terminé » pour une tâche

- Le code est fusionné et les tests liés passent.
- Les scénarios concernés sont mis à jour dans `avancement.md`.
- Toute nouvelle source a sa ligne dans `sources_registry.csv`.
- Toute nouvelle hypothèse est notée dans la documentation concernée.

## Risques du projet

| Risque | Parade |
|---|---|
| Accès AWS tardif ou limité | Pipeline exécutable en local ; interface `llm_client` ; P4 isolée |
| Temps passé sur le graphe | Version radiale fixe d'abord ; données de 5 sociétés saisies à la main et sourcées |
| Données ESG difficiles à sourcer | Périmètre réduit : composition d'ESGV + rapports de quelques émetteurs ; « information manquante » assumée |
| Latence des agents en démo | Runs des personas enregistrés + un run en direct |
| Sortie de modèle invalide | Schémas stricts, une relance, échec propre visible |
| Dérive de périmètre | Règle de priorité ci-dessus ; extras numérotés |

## Questions ouvertes

1. Dates limites et format de remise.
2. Compte AWS : services, région, modèles, budget.
3. Taille de l'équipe et répartition.
4. Nom et sous-titre de l'application.
5. Dépôt public ou privé (incidence sur les données versionnées).
