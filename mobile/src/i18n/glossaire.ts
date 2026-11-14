/**
 * Définitions en une phrase des termes techniques. Conception : docs/07_UX_UI.md (principe 2).
 */
export const glossaire: Record<string, { terme: string; definition: string }> = {
  volatilite: {
    terme: "Volatilité",
    definition: "L'ampleur des variations de prix d'un jour à l'autre, ramenée à l'année. Plus elle est élevée, plus le prix bouge.",
  },
  perte_max: {
    terme: "Perte maximale",
    definition: "La pire baisse observée entre un sommet et le creux qui a suivi, sur la période étudiée.",
  },
  pire_periode: {
    terme: "Pire période",
    definition: "Le plus mauvais résultat observé sur une durée égale à votre horizon, toutes dates de départ confondues.",
  },
  rendement_annualise: {
    terme: "Rendement annualisé observé",
    definition: "Ce qu'aurait rapporté l'actif par an, en moyenne, sur la période passée indiquée. Ce n'est pas une prévision.",
  },
  correlation: {
    terme: "Corrélation",
    definition: "Mesure à quel point deux actifs montent et baissent en même temps. Des actifs peu corrélés se diversifient mieux.",
  },
  fnb: {
    terme: "FNB",
    definition: "Fonds négocié en bourse : un panier de titres qui s'achète comme une seule action.",
  },
  esg: {
    terme: "ESG",
    definition: "Critères environnementaux, sociaux et de gouvernance, documentés par des sources publiques datées.",
  },
  diversification: {
    terme: "Diversification",
    definition: "Répartir sur des actifs qui ne réagissent pas tous de la même façon, pour ne pas dépendre d'un seul.",
  },
  adequation: {
    terme: "Adéquation au profil",
    definition: "À quel point une piste correspond aux poids et aux règles de votre profil fictif. Ce n'est pas une recommandation.",
  },
  point_in_time: {
    terme: "Point-in-time",
    definition: "L'analyse à une date donnée n'utilise que ce qui était publié à cette date : aucune donnée du futur.",
  },
};
