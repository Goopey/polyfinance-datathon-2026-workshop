/**
 * DONNÉES ENTIÈREMENT FICTIVES pour le développement de l'interface (EXPO_PUBLIC_USE_MOCKS=true).
 * Aucun actif réel, aucun chiffre réel. Les vrais chiffres viendront de la couche de validation (backend).
 *
 * Seules les personas (data/reference/personas.json) et la liste des sources
 * (data/reference/sources_registry.csv) sont réelles : ce sont des fichiers de référence de l'équipe.
 */
import type {
  AssetSummary, Criterion, DependencyGraph, Evidence, PriceSeries, QualityCheck, SentimentView, SourceInfo,
} from "../types/contracts";

export const MOCK_AS_OF = "2026-11-12";
const RETRIEVED = "2026-11-13";
const WINDOW = { start: "2021-11-12", end: MOCK_AS_OF };

export interface MockAsset extends AssetSummary {
  /** Valeurs fictives, en points de pourcentage. */
  m: { rendement_annualise: number; volatilite: number; perte_max: number; pire_periode: number; obs: number };
  /** Scores par critère dans [0, 1] (hors préférences, voir `pref`). */
  s: Omit<Record<Criterion, number>, "preferences">;
  pref: { amira: number; mateo: number; robert: number; defaut: number };
  speculative: boolean;
  controversy: boolean; // controverse documentée (fictive)
  esgKnown: boolean;
  techOrCrypto: boolean;
}

export const ASSETS: MockAsset[] = [
  {
    ticker: "ACTIF_A", name: "Société fictive A", asset_class: "equity", sector: "Technologie", currency: "USD",
    m: { rendement_annualise: 22.0, volatilite: 38.0, perte_max: -45.0, pire_periode: -8.0, obs: 1255 },
    s: { croissance: 0.85, stabilite: 0.25, diversification: 0.4, esg: 0.3, qualite: 0.8, horizon: 0.35 },
    pref: { amira: 0.95, mateo: 0.5, robert: 0.3, defaut: 0.5 },
    speculative: false, controversy: false, esgKnown: false, techOrCrypto: true,
  },
  {
    ticker: "ACTIF_D", name: "Banque fictive D", asset_class: "equity", sector: "Finance", currency: "CAD",
    m: { rendement_annualise: 7.5, volatilite: 17.0, perte_max: -22.0, pire_periode: 1.5, obs: 1251 },
    s: { croissance: 0.45, stabilite: 0.7, diversification: 0.55, esg: 0.55, qualite: 0.8, horizon: 0.75 },
    pref: { amira: 0.3, mateo: 0.5, robert: 0.9, defaut: 0.5 },
    speculative: false, controversy: false, esgKnown: true, techOrCrypto: false,
  },
  {
    ticker: "ACTIF_F", name: "Énergie fictive F", asset_class: "equity", sector: "Énergie", currency: "CAD",
    m: { rendement_annualise: 11.0, volatilite: 26.0, perte_max: -30.0, pire_periode: -2.0, obs: 1251 },
    s: { croissance: 0.6, stabilite: 0.5, diversification: 0.7, esg: 0.1, qualite: 0.6, horizon: 0.6 },
    pref: { amira: 0.4, mateo: 0.2, robert: 0.6, defaut: 0.4 },
    speculative: false, controversy: true, esgKnown: true, techOrCrypto: false,
  },
  {
    ticker: "ACTIF_G", name: "Société médiatisée fictive G", asset_class: "equity", sector: "Technologie", currency: "USD",
    m: { rendement_annualise: 35.0, volatilite: 62.0, perte_max: -68.0, pire_periode: -25.0, obs: 1255 },
    s: { croissance: 0.95, stabilite: 0.05, diversification: 0.3, esg: 0.4, qualite: 0.45, horizon: 0.1 },
    pref: { amira: 0.9, mateo: 0.4, robert: 0.7, defaut: 0.5 },
    speculative: true, controversy: false, esgKnown: true, techOrCrypto: true,
  },
  {
    ticker: "FNB_B", name: "FNB obligataire fictif B", asset_class: "etf_bond", sector: "Obligations", currency: "CAD",
    m: { rendement_annualise: 0.8, volatilite: 7.0, perte_max: -17.0, pire_periode: -4.5, obs: 1251 },
    s: { croissance: 0.15, stabilite: 0.85, diversification: 0.9, esg: 0.55, qualite: 0.7, horizon: 0.7 },
    pref: { amira: 0.2, mateo: 0.5, robert: 0.7, defaut: 0.5 },
    speculative: false, controversy: false, esgKnown: true, techOrCrypto: false,
  },
  {
    ticker: "FNB_E", name: "FNB mondial fictif E", asset_class: "etf_equity", sector: "Diversifié mondial", currency: "CAD",
    m: { rendement_annualise: 8.5, volatilite: 15.0, perte_max: -24.0, pire_periode: 0.5, obs: 1251 },
    s: { croissance: 0.55, stabilite: 0.7, diversification: 0.85, esg: 0.5, qualite: 0.75, horizon: 0.75 },
    pref: { amira: 0.5, mateo: 0.6, robert: 0.7, defaut: 0.6 },
    speculative: false, controversy: false, esgKnown: true, techOrCrypto: false,
  },
  {
    ticker: "FNB_H", name: "FNB ESG fictif H", asset_class: "etf_equity", sector: "Diversifié ESG", currency: "USD",
    m: { rendement_annualise: 7.0, volatilite: 16.0, perte_max: -26.0, pire_periode: -1.0, obs: 1255 },
    s: { croissance: 0.5, stabilite: 0.65, diversification: 0.75, esg: 0.95, qualite: 0.7, horizon: 0.65 },
    pref: { amira: 0.4, mateo: 0.95, robert: 0.4, defaut: 0.5 },
    speculative: false, controversy: false, esgKnown: true, techOrCrypto: false,
  },
  {
    ticker: "CRYPTO_C", name: "Cryptoactif fictif C", asset_class: "crypto", sector: "Cryptoactifs", currency: "USD",
    m: { rendement_annualise: 30.0, volatilite: 70.0, perte_max: -75.0, pire_periode: -40.0, obs: 1826 },
    s: { croissance: 0.9, stabilite: 0.05, diversification: 0.65, esg: 0.15, qualite: 0.2, horizon: 0.05 },
    pref: { amira: 0.85, mateo: 0.1, robert: 0.05, defaut: 0.3 },
    speculative: true, controversy: false, esgKnown: true, techOrCrypto: true,
  },
];

export const assetByTicker = (t: string) => ASSETS.find((a) => a.ticker === t);

// ---------- Registre de preuves fictif ----------

const SRC_PRICES = { source_id: "exemple_prix", name: "Source de prix fictive", url: null };
const SRC_DOC = { source_id: "exemple_document", name: "Document fictif d'émetteur", url: null };
const SRC_PROFILE = { source_id: "personas", name: "Profil fictif (data/reference/personas.json)", url: null };

export const EVIDENCE = new Map<string, Evidence>();

function put(e: Evidence) {
  EVIDENCE.set(e.evidence_id, e);
  return e.evidence_id;
}

const METRIC_DEF = {
  rendement_annualise: {
    statement: "Rendement annualisé observé sur la fenêtre",
    processing: "adj_close ; conversion en CAD ; rendements quotidiens ; annualisation géométrique",
  },
  volatilite: {
    statement: "Volatilité annualisée observée sur la fenêtre",
    processing: "adj_close ; conversion en CAD ; écart-type des rendements quotidiens × racine du nombre de périodes par an",
  },
  perte_max: {
    statement: "Perte maximale observée sur la fenêtre",
    processing: "adj_close ; conversion en CAD ; maximum du recul depuis un sommet",
  },
  pire_periode: {
    statement: "Pire période glissante de 3 ans (rendement annualisé)",
    processing: "adj_close ; conversion en CAD ; fenêtres glissantes de 3 ans",
  },
} as const;
export type MetricKey = keyof typeof METRIC_DEF;

/** Identifiant de la preuve d'un indicateur d'un actif. */
export const evId = (ticker: string, metric: MetricKey) => `EV-EX-${ticker}-${metric}`;

for (const a of ASSETS) {
  for (const key of Object.keys(METRIC_DEF) as MetricKey[]) {
    put({
      evidence_id: evId(a.ticker, key),
      type: "metric",
      claim_kind: "FAIT",
      subject: a.ticker,
      statement: METRIC_DEF[key].statement,
      value: a.m[key],
      unit: "%",
      currency: "CAD",
      window: { ...WINDOW, observations: a.m.obs },
      observed_at: MOCK_AS_OF,
      published_at: MOCK_AS_OF,
      retrieved_at: RETRIEVED,
      source: SRC_PRICES,
      processing: METRIC_DEF[key].processing,
      produced_by: `validation.metrics.${key}@v1`,
      limits: `Valeur fictive. Décrit le passé sur 5 ans ; ne prédit rien ; biais du survivant de l'univers.${
        a.asset_class === "crypto" ? " Annualisation sur 365 jours (calendrier crypto)." : " Annualisation sur 252 séances."
      }`,
    });
  }
}

export const EV_ESG_H = put({
  evidence_id: "EV-EX-ESG-H",
  type: "esg", claim_kind: "FAIT", subject: "FNB_H",
  statement: "Méthodologie d'exclusion ESG publiée par l'émetteur du fonds (document fictif)",
  value: null, unit: null, currency: null,
  window: { start: null, end: null, observations: null },
  observed_at: "2026-03-31", published_at: "2026-04-15", retrieved_at: RETRIEVED,
  source: SRC_DOC, processing: "Lecture manuelle ; extrait court", produced_by: "ingestion.esg@v1",
  limits: "Document fictif. Signal déclaratif de l'émetteur, non audité.",
});

export const EV_CONTROVERSE_F = put({
  evidence_id: "EV-EX-ESG-F",
  type: "esg", claim_kind: "FAIT", subject: "ACTIF_F",
  statement: "Controverse environnementale documentée dans un dépôt réglementaire (document fictif)",
  value: null, unit: null, currency: null,
  window: { start: null, end: null, observations: null },
  observed_at: "2025-09-30", published_at: "2025-10-20", retrieved_at: RETRIEVED,
  source: SRC_DOC, processing: "Lecture manuelle ; extrait court", produced_by: "ingestion.esg@v1",
  limits: "Document fictif. Une controverse documentée ne mesure pas l'ensemble des pratiques.",
});

export const EV_NEWS_G = put({
  evidence_id: "EV-EX-NEWS-G",
  type: "news", claim_kind: "FAIT", subject: "ACTIF_G",
  statement: "Communiqué de l'émetteur annonçant un nouveau produit (document fictif)",
  value: null, unit: null, currency: null,
  window: { start: null, end: null, observations: null },
  observed_at: "2026-10-02", published_at: "2026-10-02", retrieved_at: RETRIEVED,
  source: SRC_DOC, processing: "Date de publication du communiqué ; aucun calcul", produced_by: "ingestion.news@v1",
  limits: "Document fictif. Une annonce n'indique rien sur l'évolution future du prix.",
});

/** Preuve de type `profile` : règle ou poids issu du profil. */
export function profileEvidence(profileId: string, field: string, statement: string, value: number | null, unit: string | null) {
  const id = `EV-EX-PROFIL-${profileId}-${field}`;
  if (!EVIDENCE.has(id)) {
    put({
      evidence_id: id, type: "profile", claim_kind: "HYPOTHESE", subject: profileId,
      statement, value, unit, currency: null,
      window: { start: null, end: null, observations: null },
      observed_at: MOCK_AS_OF, published_at: MOCK_AS_OF, retrieved_at: null,
      source: SRC_PROFILE, processing: "Poids et seuils de départ fixés par l'équipe, à calibrer",
      produced_by: "agents.profile_weighting@v1",
      limits: "Hypothèse de l'équipe, pas une observation de marché.",
    });
  }
  return id;
}

let scenarioCounter = 0;
export function scenarioEvidence(subject: string, statement: string, value: number) {
  scenarioCounter += 1;
  return put({
    evidence_id: `EV-EX-SCN-${scenarioCounter}`,
    type: "metric", claim_kind: "SCENARIO", subject, statement, value, unit: "%", currency: "CAD",
    window: { ...WINDOW, observations: null },
    observed_at: MOCK_AS_OF, published_at: MOCK_AS_OF, retrieved_at: null,
    source: SRC_PRICES,
    processing: "Moyenne des volatilités pondérée par des parts égales fictives ; corrélations ignorées (approximation)",
    produced_by: "engine.coherence@v1",
    limits: "Scénario fictif : panier simulé, aucune transaction. L'approximation sans corrélations surestime la volatilité d'un panier diversifié.",
  });
}

// ---------- Graphe de dépendances fictif ----------

function relationEv(id: string, subject: string, statement: string, published: string) {
  return put({
    evidence_id: id, type: "relation", claim_kind: "FAIT", subject, statement,
    value: null, unit: null, currency: null,
    window: { start: null, end: null, observations: null },
    observed_at: published, published_at: published, retrieved_at: RETRIEVED,
    source: SRC_DOC, processing: "Saisie manuelle depuis la section « Activités » d'un rapport annuel fictif",
    produced_by: "graph.edges@v1", limits: "Document fictif. Une relation déclarée n'en donne pas l'importance financière.",
  });
}

export const GRAPHS: Record<string, DependencyGraph> = {
  ACTIF_A: {
    center: "ACTIF_A",
    nodes: [
      { id: "ACTIF_A", label: "Société fictive A", in_universe: true },
      { id: "FOURN_1", label: "Fournisseur fictif 1", in_universe: false },
      { id: "FOURN_2", label: "Fournisseur fictif 2", in_universe: false },
      { id: "CLIENT_1", label: "Client fictif 1", in_universe: false },
      { id: "ACTIF_G", label: "Société médiatisée fictive G", in_universe: true },
      { id: "PART_1", label: "Partenaire fictif 1", in_universe: false },
    ],
    edges: [
      { source: "FOURN_1", target: "ACTIF_A", relation: "FOURNISSEUR", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-01", "ACTIF_A", "Fournisseur fictif 1 cité comme fournisseur principal de composants", "2026-02-20") },
      { source: "FOURN_2", target: "ACTIF_A", relation: "FOURNISSEUR", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-02", "ACTIF_A", "Fournisseur fictif 2 cité comme fournisseur de services infonuagiques", "2026-02-20") },
      { source: "ACTIF_A", target: "CLIENT_1", relation: "CLIENT", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-03", "ACTIF_A", "Client fictif 1 cité comme client important", "2026-02-20") },
      { source: "ACTIF_A", target: "ACTIF_G", relation: "CONCURRENT", claim_kind: "HYPOTHESE", evidence_id: null },
      { source: "ACTIF_A", target: "PART_1", relation: "PARTENAIRE", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-04", "ACTIF_A", "Partenariat de recherche annoncé avec Partenaire fictif 1", "2025-11-05") },
    ],
  },
  ACTIF_G: {
    center: "ACTIF_G",
    nodes: [
      { id: "ACTIF_G", label: "Société médiatisée fictive G", in_universe: true },
      { id: "FOURN_1", label: "Fournisseur fictif 1", in_universe: false },
      { id: "ACTIF_A", label: "Société fictive A", in_universe: true },
      { id: "CLIENT_2", label: "Client fictif 2", in_universe: false },
    ],
    edges: [
      { source: "FOURN_1", target: "ACTIF_G", relation: "FOURNISSEUR", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-05", "ACTIF_G", "Fournisseur fictif 1 cité comme fournisseur unique d'un composant clé", "2026-03-10") },
      { source: "ACTIF_G", target: "ACTIF_A", relation: "CONCURRENT", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-06", "ACTIF_G", "Société fictive A citée parmi les concurrents", "2026-03-10") },
      { source: "ACTIF_G", target: "CLIENT_2", relation: "CLIENT", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-07", "ACTIF_G", "Client fictif 2 représente une part importante des revenus déclarés", "2026-03-10") },
    ],
  },
  ACTIF_D: {
    center: "ACTIF_D",
    nodes: [
      { id: "ACTIF_D", label: "Banque fictive D", in_universe: true },
      { id: "CONC_3", label: "Banque concurrente fictive 3", in_universe: false },
      { id: "PART_2", label: "Partenaire de paiement fictif 2", in_universe: false },
    ],
    edges: [
      { source: "ACTIF_D", target: "CONC_3", relation: "CONCURRENT", claim_kind: "FAIT",
        evidence_id: relationEv("EV-EX-REL-08", "ACTIF_D", "Banque concurrente fictive 3 citée parmi les concurrents", "2025-12-04") },
      { source: "ACTIF_D", target: "PART_2", relation: "PARTENAIRE", claim_kind: "HYPOTHESE", evidence_id: null },
    ],
  },
};

// ---------- Données (écran « Données ») ----------

/** Recopie de data/reference/sources_registry.csv (noms et statuts réels). */
export const SOURCES: SourceInfo[] = [
  { source_id: "starter_universe", nom: "Univers d'actifs (organisateurs)", type_de_donnee: "Univers", date_extraction: "2026-11-13", limites: "Biais du survivant : univers choisi en 2026", statut: "utilisé" },
  { source_id: "starter_prices", nom: "Yahoo Finance via yfinance", type_de_donnee: "Prix quotidiens", date_extraction: "2026-11-13", limites: "Prix en devise de cotation ; adj_close", statut: "utilisé" },
  { source_id: "starter_corporate_actions", nom: "Yahoo Finance via yfinance", type_de_donnee: "Opérations sur titres", date_extraction: "2026-11-13", limites: "Anomalie CNQ.TO signalée", statut: "utilisé" },
  { source_id: "starter_fx", nom: "Banque du Canada — API Valet (FXUSDCAD)", type_de_donnee: "Change", date_extraction: "2026-11-13", limites: "Pas de taux les jours fériés", statut: "utilisé" },
  { source_id: "starter_macro_boc", nom: "Banque du Canada — API Valet", type_de_donnee: "Macro", date_extraction: "2026-11-13", limites: "Délais de publication appliqués", statut: "utilisé" },
  { source_id: "starter_macro_fred", nom: "FRED — Federal Reserve Bank of St. Louis", type_de_donnee: "Macro", date_extraction: "2026-11-13", limites: "Valeurs révisées", statut: "utilisé" },
  { source_id: "sec_edgar", nom: "SEC EDGAR", type_de_donnee: "Dépôts réglementaires", date_extraction: null, limites: "—", statut: "prévu" },
  { source_id: "sedar_plus", nom: "SEDAR+", type_de_donnee: "Dépôts réglementaires", date_extraction: null, limites: "—", statut: "prévu" },
  { source_id: "etf_issuers", nom: "Sites des émetteurs de FNB", type_de_donnee: "Composition", date_extraction: null, limites: "—", statut: "prévu" },
  { source_id: "issuer_sustainability", nom: "Rapports de durabilité des sociétés", type_de_donnee: "ESG", date_extraction: null, limites: "—", statut: "prévu" },
  { source_id: "alpaca_market_data", nom: "Alpaca — données de marché", type_de_donnee: "Prix", date_extraction: null, limites: "Conditions à vérifier", statut: "optionnel — désactivé" },
  { source_id: "finnhub", nom: "Finnhub", type_de_donnee: "Prix, nouvelles", date_extraction: null, limites: "Licence d'usage personnel à vérifier", statut: "optionnel — désactivé" },
];

/** Contrôles qualité fictifs (le vrai rapport est data/curated/quality_report.json, servi par l'API). */
export const QUALITY: QualityCheck[] = [
  { check: "Doublons (date, ticker)", status: "ok", details: [] },
  { check: "Prix nuls ou négatifs", status: "ok", details: [] },
  { check: "Volumes nuls", status: "avertissement", details: ["ACTIF_D : une séance à volume nul (fictif)"] },
  { check: "Trous de plus de 5 séances", status: "ok", details: [] },
  { check: "Variations journalières de plus de 25 %", status: "avertissement", details: ["CRYPTO_C : 2 séances, rapprochées des opérations sur titres (fictif)"] },
  { check: "Couverture du change", status: "ok", details: [] },
  { check: "Observations minimales (252)", status: "ok", details: [] },
  { check: "Fractionnements suspects", status: "ok", details: [] },
];

// ---------- Sentiment et cours fictifs (fiche d'un actif) ----------

const SRC_SENTIMENT = { source_id: "exemple_sentiment", name: "Source de sentiment fictive", url: null };

/** Petit générateur pseudo-aléatoire déterministe (même série à chaque chargement). */
function seeded(text: string) {
  let s = [...text].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Sentiment fictif d'une action (null pour les FNB et la crypto, comme l'API). */
export function mockSentiment(a: MockAsset): SentimentView | null {
  if (a.asset_class !== "equity") return null;
  const r = seeded(`${a.ticker}-sentiment`);
  const counts = {
    strong_buy: Math.round(r() * 10), buy: Math.round(4 + r() * 16), hold: Math.round(3 + r() * 12),
    sell: Math.round(r() * 4), strong_sell: Math.round(r() * 2),
  };
  const total = Object.values(counts).reduce((x, y) => x + y, 0);
  const balance = Math.round(((counts.strong_buy + counts.buy - counts.sell - counts.strong_sell) / total) * 100) / 100;
  const analystsId = put({
    evidence_id: `EV-EX-${a.ticker}-analystes`,
    type: "metric", claim_kind: "FAIT", subject: a.ticker,
    statement: `Recommandations d'analystes, octobre 2026 : ${counts.strong_buy} achat fort, ${counts.buy} achat, ${counts.hold} conserver, ${counts.sell} vente, ${counts.strong_sell} vente forte (fictif)`,
    value: balance, unit: "ratio", currency: null,
    window: { start: null, end: null, observations: null },
    observed_at: "2026-10-01", published_at: "2026-10-31", retrieved_at: RETRIEVED,
    source: SRC_SENTIMENT, processing: "Solde = (achats − ventes) ÷ total des recommandations", produced_by: "data.sentiment@v1",
    limits: "Données fictives. Opinions d'analystes, pas une prévision ; sans effet sur le score.",
  });
  const label = balance >= 0.5 ? "positif" : balance < 0.1 ? "négatif" : "neutre";
  const mspr = Math.round((r() * 120 - 60) * 10) / 10;
  const insidersId = a.currency === "USD"
    ? put({
      evidence_id: `EV-EX-${a.ticker}-inities`,
      type: "metric", claim_kind: "FAIT", subject: a.ticker,
      statement: "Indice de sentiment des initiés (MSPR, de -100 à +100), octobre 2026 (fictif)",
      value: mspr, unit: "indice", currency: null,
      window: { start: null, end: null, observations: null },
      observed_at: "2026-10-01", published_at: "2026-11-05", retrieved_at: RETRIEVED,
      source: SRC_SENTIMENT, processing: "Achats et ventes des dirigeants, agrégés par mois", produced_by: "data.sentiment@v1",
      limits: "Données fictives. Sociétés américaines seulement.",
    })
    : null;
  return {
    label,
    analysts: { period: "2026-10-01", ...counts, balance, evidence_id: analystsId },
    insiders: insidersId ? { period: "2026-10-01", mspr, evidence_id: insidersId } : null,
  };
}

/** Cours hebdomadaires fictifs, cohérents avec le rendement et la volatilité fictifs de l'actif. */
export function mockPrices(a: MockAsset): PriceSeries {
  const r = seeded(`${a.ticker}-prix`);
  const weeks = 261;
  const drift = Math.log(1 + a.m.rendement_annualise / 100) / 52;
  const vol = a.m.volatilite / 100 / Math.sqrt(52);
  const start = new Date(`${WINDOW.start}T00:00:00Z`);
  const points: { day: string; value: number }[] = [];
  let value = 100;
  for (let i = 0; i < weeks; i++) {
    const day = new Date(start.getTime() + i * 7 * 86400000);
    if (i > 0) {
      const shock = (r() + r() + r() + r() - 2) * Math.sqrt(3); // ≈ loi normale centrée réduite
      value *= Math.exp(drift - (vol * vol) / 2 + vol * shock);
    }
    points.push({ day: day.toISOString().slice(0, 10), value: Math.round(value * 100) / 100 });
  }
  points[points.length - 1].day = MOCK_AS_OF;
  return {
    ticker: a.ticker, currency: "CAD", as_of: MOCK_AS_OF, start: points[0].day, end: MOCK_AS_OF, points,
    change_pct: Math.round((points[points.length - 1].value / points[0].value - 1) * 10000) / 100,
    evidence_id: evId(a.ticker, "rendement_annualise"),
  };
}
