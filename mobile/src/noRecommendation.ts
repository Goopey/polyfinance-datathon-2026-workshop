/**
 * État « Aucune recommandation » : lecture de la raison donnée par le moteur (engine/decision.py).
 * Fonctions pures (testées dans tests/noRecommendation.test.ts).
 */
import type { Criterion } from "./types/contracts";

const NO_RECO_PREFIX = /^Aucune recommandation\s*:\s*/;

/** « Aucune recommandation : le critère… » → « Le critère… » (le titre de la carte le dit déjà). */
export function stripNoRecoPrefix(text: string): string {
  const rest = text.replace(NO_RECO_PREFIX, "");
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

/** Libellés du moteur (backend/easytrade/schemas/weights.py, CRITERION_LABELS) → critère. */
const BACKEND_CRITERION: Record<string, Criterion> = {
  croissance: "croissance", "stabilité": "stabilite", diversification: "diversification", ESG: "esg",
  "qualité": "qualite", "tenue sur l'horizon": "horizon", "préférences déclarées": "preferences",
};

/** Critère prioritaire sans donnée cité par le moteur, sinon null (autre cause : rien à proposer). */
export function blockingCriterion(text: string): Criterion | null {
  const m = /le critère le plus important de votre profil \((.+?), \d+[\s  ]?%\)/i.exec(text);
  return m ? BACKEND_CRITERION[m[1]] ?? null : null;
}
