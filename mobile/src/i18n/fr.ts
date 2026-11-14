/**
 * Textes de l'interface (français). Vocabulaire non prescriptif : docs/07_UX_UI.md, section Rédaction.
 */
import type {
  ClaimKind, Confidence, Criterion, Fit, RunStepId, Stance, StepStatus, Verdict,
} from "../types/contracts";

export const fr = {
  appName: "EasyTrade",
  subtitle: "Simulateur d'aide à la décision — aucune transaction réelle",
  banner: "Simulation — aucune transaction réelle. Ceci n'est pas un conseil financier.",
  mockBanner: "Données entièrement fictives (mode développement)",

  criteria: {
    croissance: "Croissance observée",
    stabilite: "Stabilité",
    diversification: "Diversification",
    esg: "ESG",
    qualite: "Qualité",
    horizon: "Horizon",
    preferences: "Préférences",
  } satisfies Record<Criterion, string>,

  fit: { "élevée": "Adéquation élevée", partielle: "Adéquation partielle", faible: "Adéquation faible" } satisfies Record<Fit, string>,
  confidence: { "élevée": "Confiance élevée", moyenne: "Confiance moyenne", faible: "Confiance faible" } satisfies Record<Confidence, string>,
  stance: { appui: "Appui", appui_reserve: "Appui avec réserve", opposition: "Opposition" } satisfies Record<Stance, string>,
  agent: { bull: "Bull — arguments pour", realist: "Réaliste — cas de base", bear: "Bear — risques" },
  claimKind: { FAIT: "Fait", HYPOTHESE: "Hypothèse", SCENARIO: "Scénario fictif" } satisfies Record<ClaimKind, string>,
  verdict: {
    "cohérent": "Cohérent avec le profil",
    "cohérent avec réserve": "Cohérent avec réserve",
    "incohérent avec le profil": "Incohérent avec le profil",
  } satisfies Record<Verdict, string>,

  steps: {
    profil: "Profil",
    recherche_validation: "Recherche et validation",
    debat: "Débat",
    decision: "Décision",
    explication: "Explication",
  } satisfies Record<RunStepId, string>,
  stepStatus: { attente: "En attente", en_cours: "En cours", ok: "Terminé", echec: "Échec" } satisfies Record<StepStatus, string>,

  relation: { FOURNISSEUR: "Fournisseur", CLIENT: "Client", CONCURRENT: "Concurrent", PARTENAIRE: "Partenaire" },
  assetClass: {
    equity: "Action", etf_equity: "FNB d'actions", etf_bond: "FNB d'obligations", etf: "FNB", crypto: "Cryptoactif",
  } as Record<string, string>,

  unknownsTitle: "Ce que nous ne savons pas",
  rejectedTitle: "Écartées et pourquoi",
  noRecoTitle: "Aucune piste à explorer pour ce profil",
  noRecoBody: "Le système préfère ne rien proposer plutôt que de forcer une piste. Voici ce qui manque :",
};
