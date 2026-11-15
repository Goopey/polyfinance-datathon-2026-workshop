/**
 * Définitions en une phrase des termes techniques. Conception : docs/07_UX_UI.md (principe 2).
 */
type Glossary = Record<string, { terme: string; definition: string }>;

export const glossaire: Glossary = {
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
    definition: "À quel point une piste correspond aux poids et aux règles de votre profil. Ce n'est pas une recommandation.",
  },
  point_in_time: {
    terme: "Point-in-time",
    definition: "L'analyse à une date donnée n'utilise que ce qui était publié à cette date : aucune donnée du futur.",
  },
};

export const glossaryEn: Glossary = {
  volatilite: {
    terme: "Volatility",
    definition: "How much the price moves from day to day, scaled to a year. The higher it is, the more the price swings.",
  },
  perte_max: {
    terme: "Maximum drawdown",
    definition: "The worst observed drop from a peak to the trough that followed, over the period studied.",
  },
  pire_periode: {
    terme: "Worst period",
    definition: "The worst result observed over a span equal to your horizon, across all possible start dates.",
  },
  rendement_annualise: {
    terme: "Observed annualized return",
    definition: "What the asset would have returned per year, on average, over the past period shown. It is not a forecast.",
  },
  correlation: {
    terme: "Correlation",
    definition: "How much two assets rise and fall together. Weakly correlated assets diversify better.",
  },
  fnb: {
    terme: "ETF",
    definition: "Exchange-traded fund: a basket of securities you can buy like a single stock.",
  },
  esg: {
    terme: "ESG",
    definition: "Environmental, social and governance criteria, documented by dated public sources.",
  },
  diversification: {
    terme: "Diversification",
    definition: "Spreading across assets that don't all react the same way, so you don't depend on just one.",
  },
  adequation: {
    terme: "Profile fit",
    definition: "How closely an idea matches your profile's weights and rules. It is not a recommendation.",
  },
  point_in_time: {
    terme: "Point-in-time",
    definition: "An analysis at a given date only uses what was published by that date: no data from the future.",
  },
};
