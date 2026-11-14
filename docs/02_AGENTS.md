# 02 — Agents

Le jury posera une question par composant : **« Pourquoi cet agent existe-t-il et quelle valeur apporte-t-il ? »** Chaque fiche y répond en premier.

Règles communes :

- Sortie = JSON conforme à un schéma. Une sortie invalide est rejetée et relancée une fois, puis l'étape échoue proprement.
- Un agent ne produit **aucun chiffre** : il cite des `evidence_id`. Les chiffres viennent de la couche de validation.
- On enregistre les **actions observables** (entrées, outils appelés, sorties), pas le raisonnement interne du modèle.
- Les prompts sont versionnés dans `backend/easytrade/agents/prompts/`.

---

## 1. Agent de pondération du profil

**Pourquoi il existe.** Transformer un profil exprimé en langage courant en paramètres que le moteur peut appliquer, et rendre ce passage visible.

| | |
|---|---|
| Entrée | `Profile` (objectif, tolérance, horizon, contraintes, préférences ; champs libres permis) |
| Sortie | `ProfileWeights` : contraintes dures, poids par critère, justification courte de chaque valeur, informations manquantes |
| Outils | Aucun |
| Garde-fous | Poids bornés et normalisés par le code ; un gabarit par niveau de risque sert de point de départ ; écarts au gabarit listés |

```json
{
  "profile_id": "amira",
  "hard_constraints": {
    "max_weight_per_asset": 0.15,
    "max_weight_per_sector": 0.40,
    "max_weight_crypto": 0.15,
    "excluded_asset_classes": [],
    "esg_exclusion": false
  },
  "weights": {
    "croissance": 0.30, "stabilite": 0.10, "diversification": 0.20,
    "esg": 0.05, "qualite": 0.10, "horizon": 0.10, "preferences": 0.15
  },
  "rationale": [
    {"field": "weights.diversification", "because": "Souhaite éviter de miser exclusivement sur les technologies."}
  ],
  "missing_information": []
}
```

Les valeurs ci-dessus sont des **hypothèses de départ à calibrer** (voir `03_DECISION_ENGINE.md`).

---

## 2. Agent de recherche

**Pourquoi il existe.** C'est le seul composant qui décide *quoi aller chercher*. Il mobilise les outils de données selon le profil : c'est le cœur agentique.

| | |
|---|---|
| Entrée | `ProfileWeights`, univers d'actifs, `as_of`, `requested_ticker` éventuel |
| Sortie | `CandidateList` : candidats, motif de présélection, preuves qualitatives rattachées |
| Outils | `lister_univers`, `chercher_documents` (dépôts EDGAR / SEDAR+), `preuves_esg`, `relations` (graphe), `nouvelles` (si source autorisée) |
| Garde-fous | Les outils filtrent sur `published_at ≤ as_of` ; chaque candidat doit porter au moins une preuve ; un titre demandé par l'utilisateur est toujours analysé, jamais filtré en silence |

---

## Couche de validation financière (pas un agent)

**Pourquoi elle existe.** Les chiffres ne doivent pas dépendre d'un modèle de langage. Tout est du Python déterministe, testé, rejouable.

| | |
|---|---|
| Entrée | Prix, opérations sur titres, change, macro, `as_of` |
| Sortie | `MetricsTable` + une preuve (`type = metric`) par indicateur |
| Indicateurs | Rendement annualisé, volatilité annualisée, perte maximale (drawdown), pire période glissante sur l'horizon, corrélations, concentration sectorielle, comportement en 2022 |
| Contrôles | Fenêtre explicite, nombre d'observations, devise, alignement de calendrier, données manquantes |

Chaque indicateur est accompagné de sa fenêtre et de sa limite d'interprétation : ce sont des **descriptions du passé**, pas des prévisions.

---

## 3. Conseil de débat : Bull, Réaliste, Bear

**Pourquoi il existe.** Un seul modèle a tendance à confirmer la question posée. Trois points de vue obligés de s'appuyer sur les mêmes preuves font apparaître les compromis et l'incertitude, que l'on conserve au lieu de les lisser.

| Agent | Mandat |
|---|---|
| Bull | Meilleurs arguments en faveur : potentiel, catalyseurs documentés |
| Réaliste | Cas de base, compromis, adéquation au profil |
| Bear | Risques, faiblesses, incohérences avec le profil |

Entrée identique pour les trois : `EvidencePack` du candidat + `ProfileWeights`.

### Protocole

| Tour | Contenu | MVP |
|---|---|:-:|
| 1 | Analyse indépendante, en parallèle | ✔ |
| 2 | Contre-examen : chacun répond aux deux autres | extra |
| 3 | Position finale : appui, appui avec réserve, opposition + niveau de confiance | ✔ |

```json
{
  "ticker": "NVDA",
  "agent": "bear",
  "round": 3,
  "stance": "opposition",
  "confidence": "moyenne",
  "arguments": [
    {"text": "Perte maximale élevée sur la fenêtre observée.", "evidence_ids": ["EV-000412"], "claim_kind": "FAIT"}
  ],
  "open_questions": ["Aucune preuve ESG datée disponible."]
}
```

Garde-fous : un argument sans `evidence_id` valide est supprimé par le code ; les arguments sont courts et factuels ; la dissidence est conservée telle quelle dans `Decision.disagreements`.

---

## 4. Moteur de décision (pas un agent)

**Pourquoi il existe.** La décision doit être vérifiable. Détail dans `03_DECISION_ENGINE.md`.

Entrées : `ProfileWeights`, `MetricsTable`, `DebateRecord[]`. Sortie : `Decision` (classement, rejets motivés, désaccords, tensions profil/demande, ou « aucune recommandation »).

---

## 5. Agent d'explication

**Pourquoi il existe.** Rendre le résultat compréhensible par quelqu'un qui n'est pas du métier, sans rien ajouter aux preuves.

| | |
|---|---|
| Entrée | `Decision`, `EvidencePack[]`, `DebateRecord[]`, `ProfileWeights`, niveau de lecture (Simple / Avancé) |
| Sortie | `Explanation` : résumé, lien au profil, synthèse du débat, risques et limites, opportunités écartées, citations |
| Garde-fous | Vérificateur de fidélité (`explain/fidelity.py`) : chaque nombre du texte doit correspondre à une preuve ; chaque phrase affirmative porte une citation ; formulations prescriptives refusées (Bedrock Guardrails + liste de termes) |

```json
{
  "run_id": "run_2026-11-12_amira",
  "as_of": "2026-11-12",
  "headline": "3 pistes cohérentes avec votre profil, 2 écartées",
  "items": [
    {
      "ticker": "…",
      "fit": "élevée",
      "why": [{"text": "…", "evidence_ids": ["EV-…"], "claim_kind": "FAIT"}],
      "debate_summary": {"bull": "…", "realist": "…", "bear": "…", "dissent": true},
      "risks": ["…"],
      "limits": ["Fenêtre de 5 ans ; biais du survivant de l'univers."]
    }
  ],
  "rejected": [{"ticker": "…", "reason": "Contrainte : part crypto maximale atteinte."}],
  "disclaimer": "Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier."
}
```

---

## Modèles

Le choix dépend des modèles ouverts dans le compte AWS du datathon (à confirmer). Principe : un modèle rapide pour les tours de débat, un modèle plus fort pour la recherche et l'explication. L'identifiant du modèle est enregistré dans la trace de chaque étape.
