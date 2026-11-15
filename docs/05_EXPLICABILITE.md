# 05 — Explicabilité

Exigence du case : des explications **synthétiques, vérifiables, fidèles aux sources et aux actions observables**, sans justification inventée après coup et sans exposer le raisonnement interne détaillé des modèles.

Notre mécanisme repose sur trois objets : le registre de preuves, la trace d'exécution et le vérificateur de fidélité.

## 1. Registre de preuves

Toute donnée citée est une preuve identifiée.

```json
{
  "evidence_id": "EV-000412",
  "type": "metric",
  "claim_kind": "FAIT",
  "subject": "NVDA",
  "statement": "Perte maximale sur la fenêtre observée",
  "value": null,
  "unit": "%",
  "currency": "USD",
  "window": {"start": "2021-11-12", "end": "2026-11-12", "observations": null},
  "observed_at": "2026-11-12",
  "published_at": "2026-11-12",
  "retrieved_at": "2026-11-13",
  "source": {"source_id": "starter_prices", "name": "Yahoo Finance via yfinance", "url": "https://finance.yahoo.com"},
  "processing": "adj_close ; rendements quotidiens ; maximum du recul depuis un sommet",
  "produced_by": "validation.metrics.max_drawdown@v1",
  "limits": "Décrit le passé sur 5 ans ; biais du survivant de l'univers."
}
```

`type` ∈ `metric | filing | esg | relation | macro | news | profile`.

Les valeurs `null` de l'exemple seront remplies par le calcul réel : aucun chiffre n'est écrit à la main dans la documentation.

## 2. Fait, hypothèse, scénario

| `claim_kind` | Définition | Rendu dans l'application |
|---|---|---|
| `FAIT` | Donnée observée, source et date citées | Texte normal + pastille de source |
| `HYPOTHESE` | Choix de l'équipe ou du système (poids, seuils, relation non confirmée) | Étiquette « Hypothèse » |
| `SCENARIO` | Simulation fictive (« si la part crypto passait à 10 % ») | Étiquette « Scénario fictif » |

## 3. Trace d'exécution

On enregistre ce qui a été fait, pas ce que le modèle a « pensé ».

```json
{
  "run_id": "run_…",
  "as_of": "2026-11-12",
  "profile_id": "robert",
  "steps": [
    {
      "step": "validation",
      "kind": "code",
      "started_at": "…", "ended_at": "…", "status": "ok",
      "inputs": ["s3://…/curated/prices.parquet"],
      "outputs": ["EV-000401", "EV-000412"],
      "version": "validation@v1"
    },
    {
      "step": "debate.bear.round1",
      "kind": "llm",
      "model_id": "…",
      "prompt_version": "bear@v1",
      "tools_called": [],
      "evidence_in": ["EV-000401", "EV-000412"],
      "output_ref": "s3://…/runs/run_…/debate_bear_r1.json",
      "status": "ok"
    }
  ]
}
```

Sur AWS, cette trace correspond à l'historique d'exécution de la machine d'états Step Functions, complété par les journaux CloudWatch.

## 4. Vérificateur de fidélité

Avant affichage, `explain/fidelity.py` contrôle la sortie de l'agent d'explication :

1. Chaque nombre du texte correspond à la valeur d'une preuve citée (tolérance d'arrondi définie).
2. Chaque affirmation porte au moins un `evidence_id` existant dans le run.
3. Aucune preuve citée n'a `published_at > as_of`.
4. Aucune formulation prescriptive (« achetez », « vous devriez investir », « garanti »).
5. Le `claim_kind` affiché est celui de la preuve.

En cas d'échec : une relance avec le motif ; si l'échec persiste, la phrase fautive est retirée et l'incident est noté dans la trace. Le taux de réussite est un indicateur de validation à présenter au jury (scénario S6).

Précisions de réalisation (P3, `explain/fidelity.py`) :

- **Insertion des valeurs.** Un agent écrit `{EV-000123}` là où une valeur doit apparaître ; le code y insère la valeur de la preuve (pourcentage à une décimale, ratio à deux). Aucun chiffre n'est donc écrit par un modèle ; le contrôle 1 s'applique quand même au texte final.
- **Tolérance d'arrondi.** Un nombre du texte est étayé s'il est à moins d'un demi-pas de la valeur d'une preuve citée, le pas étant la dernière décimale écrite (« 35 % » accepte 34,5 à 35,5 ; « 35,2 % » accepte 35,15 à 35,25). Le signe est ignoré (« perte maximale de 42 % » pour −41,6).
- **Nombres de l'énoncé.** Un nombre qui figure dans l'énoncé ou la fenêtre d'une preuve citée est admis (« pire période glissante de 3 ans », « année 2022 »). Les noms d'actifs (« S&P 500 »), les dates et les identifiants de preuve ne sont pas lus comme des chiffres.
- **`claim_kind`.** Celui des preuves citées : SCENARIO l'emporte sur HYPOTHESE, qui l'emporte sur FAIT. Un écart est corrigé par le code et compté.
- **Portée.** Mêmes contrôles sur les arguments du débat (un argument fautif est supprimé) et sur les textes produits par le moteur (tensions, motifs de rejet). La sortie complète est recontrôlée avant affichage ; s'il reste un écart, elle n'est pas affichée et le run échoue de façon visible.
- **Mesure.** `FidelityReport` : affirmations rédigées fidèles au premier passage, relance, retraits, affirmations recontrôlées. Valeurs mesurées : `avancement.md`, scénario S6.

## 5. Dans l'interface

| Élément | Comportement |
|---|---|
| Pastille de source | Sous chaque chiffre ; ouvre la preuve : source, dates, traitement, limites |
| Bouton « Pourquoi ? » | Sur chaque piste : contribution des critères, contraintes appliquées, synthèse du débat |
| « Ce que nous ne savons pas » | Bloc systématique : informations manquantes, limites de la fenêtre, désaccords |
| Écran « Parcours de l'analyse » | Les étapes exécutées, dans l'ordre, avec statut et durée |
| Étiquettes Hypothèse / Scénario | Visibles sans action de l'utilisateur |

## 6. Exemple attendu dans la documentation technique

Le livrable demande « un exemple reliant une conclusion aux données ou aux traces d'exécution observables ». Format prévu, à remplir avec un run réel :

> **Conclusion** : « [Titre] est jugé incohérent avec le profil de Robert. »
> **Étayée par** : EV-… (volatilité), EV-… (perte maximale), EV-… (pire période glissante de 3 ans), contrainte `horizon 3-5 ans` du profil.
> **Étapes observables** : validation → débat (Bear : opposition ; Réaliste : réserve ; Bull : appui) → moteur de décision, règle « tension profil / demande ».
> **Limites** : fenêtre de 5 ans ; aucune prévision.

## 7. Ce que l'on ne fait pas

- Pas d'affichage du raisonnement pas-à-pas des modèles.
- Pas d'explication rédigée après coup sans lien avec les étapes réellement exécutées.
- Pas de chiffre produit par un LLM.
