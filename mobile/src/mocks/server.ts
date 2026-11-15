/**
 * Serveur fictif : imite les routes de l'API (docs/01_ARCHITECTURE.md) sur les données de fixtures.ts.
 *
 * Il reproduit la *forme* du moteur de décision (contraintes dures → score pondéré → sélection →
 * cohérence d'une demande) pour que l'interface se comporte comme avec le vrai backend.
 * Ce n'est PAS le moteur : la référence est backend/easytrade/engine/ (P2). Tout chiffre est fictif.
 */
import personasJson from "../../../data/reference/personas.json";
import { fr } from "../i18n/fr";
import { fmtPct, fmtWeight } from "../format";
import {
  CRITERIA, RUN_STEPS,
  type AssetMetric, type AssetSheet, type AssetSummary, type Claim, type CoherenceAnalysis, type Confidence,
  type Criterion, type CriterionMap, type DataOverview, type DebatePosition, type DependencyGraph, type Evidence,
  type Explanation, type ExplanationItem, type Fit, type Persona, type ProfileDraft, type ProfileWeights,
  type RejectedItem, type RunRequest, type RunStatus, type Stance, type Trace, type TraceStep, type Verdict,
} from "../types/contracts";
import {
  ASSETS, EVIDENCE, EV_CONTROVERSE_F, EV_ESG_H, EV_NEWS_G, GRAPHS, MOCK_AS_OF, QUALITY, SOURCES,
  assetByTicker, evId, profileEvidence, scenarioEvidence, type MetricKey, type MockAsset,
} from "./fixtures";

export class MockNotFound extends Error {}
export class MockInvalid extends Error {}

export const PREFERENCES = ["esg", "technologies", "stabilite", "diversification"];
export const EXCLUSIONS = ["crypto", "speculatif", "controverses"];

const PERSONAS = (personasJson as unknown as { personas: Persona[] }).personas;
// Durée fictive d'une étape ; les tests la réduisent (EXPO_PUBLIC_MOCK_STEP_MS).
const STEP_MS = Number(process.env.EXPO_PUBLIC_MOCK_STEP_MS ?? 900);
const MAX_PISTES = 4;
const DISCLAIMER = "Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier.";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ---------- Profils ----------

type Tolerance = ProfileDraft["tolerance"];
type Horizon = ProfileDraft["horizon"];

interface MockProfile {
  pw: ProfileWeights;
  tolerance: Tolerance;
  horizon: Horizon;
  horizonLabel: string;
  speculatif: "permis" | "exclu" | "signalé";
  concentrationRule: boolean; // « éviter de miser exclusivement sur les technologies »
  prefKey: keyof MockAsset["pref"];
}

/** Seuils indicatifs par tolérance : HYPOTHESES de l'équipe, à calibrer (docs/03_DECISION_ENGINE.md). */
const LIMITS: Record<Tolerance, { vol: number; dd: number }> = {
  faible: { vol: 18, dd: 20 },
  moderee: { vol: 25, dd: 30 },
  elevee: { vol: 45, dd: 50 },
};

const PROFILES = new Map<string, MockProfile>();

function normalize(w: Partial<CriterionMap>): CriterionMap {
  const out = {} as CriterionMap;
  const total = CRITERIA.reduce((s, k) => s + Math.max(0, w[k] ?? 0), 0) || 1;
  for (const k of CRITERIA) out[k] = Math.round((Math.max(0, w[k] ?? 0) / total) * 1000) / 1000;
  return out;
}

function personaToProfile(p: Persona): MockProfile {
  const tolerance: Tolerance = p.id === "amira" ? "elevee" : p.id === "mateo" ? "moderee" : "faible";
  const h = p.profil.horizon_annees;
  const horizon: Horizon = h.min >= 12 ? "long" : h.min >= 6 ? "moyen" : "court";
  const horizonLabel = h.max ? `${h.min} à ${h.max} ans` : `${h.min} ans et plus`;
  const c = p.contraintes;
  const excluded = c.max_weight_crypto === 0 ? ["crypto"] : [];
  const rationale: ProfileWeights["rationale"] = [];
  if (p.id === "amira") {
    rationale.push({ field: "weights.diversification", because: "Souhaite éviter de miser exclusivement sur les technologies.", claim_kind: "FAIT" });
    rationale.push({ field: "hard_constraints.max_weight_crypto", because: "Intéressée par les cryptoactifs, avec un plafond pour garder la diversification.", claim_kind: "HYPOTHESE" });
  }
  if (p.id === "mateo") {
    rationale.push({ field: "weights.esg", because: "Accorde une grande importance aux facteurs ESG.", claim_kind: "FAIT" });
    rationale.push({ field: "hard_constraints.esg_exclusion", because: "Souhaite éviter les entreprises liées à des controverses importantes.", claim_kind: "FAIT" });
  }
  if (p.id === "robert") {
    rationale.push({ field: "weights.stabilite", because: "Souhaite préserver son capital ; horizon de 3 à 5 ans.", claim_kind: "FAIT" });
    rationale.push({ field: "hard_constraints.max_weight_crypto", because: "Peu intéressé par les cryptoactifs.", claim_kind: "FAIT" });
  }
  rationale.push({ field: "weights", because: "Valeurs de départ fixées par l'équipe, à calibrer.", claim_kind: "HYPOTHESE" });
  return {
    tolerance, horizon, horizonLabel,
    speculatif: c.speculatif,
    concentrationRule: p.id === "amira",
    prefKey: p.id as MockProfile["prefKey"],
    pw: {
      profile_id: p.id,
      label: p.profil.nom,
      summary: `${p.profil.nom}, ${p.profil.age} ans · risque ${p.profil.tolerance_risque} · horizon ${horizonLabel}`,
      hard_constraints: {
        max_weight_per_asset: c.max_weight_per_asset,
        max_weight_per_sector: c.max_weight_per_sector,
        max_weight_crypto: c.max_weight_crypto,
        excluded_asset_classes: excluded,
        esg_exclusion: c.esg_exclusion,
        speculatif: c.speculatif,
      },
      weights: normalize(p.poids),
      rationale,
      missing_information: p.id === "mateo" ? ["Données ESG partielles : certains actifs n'ont aucune preuve datée."] : [],
    },
  };
}

for (const p of PERSONAS) PROFILES.set(p.id, personaToProfile(p));

const TEMPLATE: Record<Tolerance, string> = { faible: "robert", moderee: "mateo", elevee: "amira" };
let customCounter = 0;

function draftToProfile(d: ProfileDraft, id: string): MockProfile {
  const base = PROFILES.get(d.base_persona ?? TEMPLATE[d.tolerance])!;
  const weights = { ...base.pw.weights };
  if (!d.base_persona) {
    if (d.preferences.includes("esg")) weights.esg += 0.1;
    if (d.preferences.includes("stabilite")) weights.stabilite += 0.1;
    if (d.preferences.includes("technologies")) weights.preferences += 0.05;
    if (d.objectif === "croissance") weights.croissance += 0.05;
    if (d.objectif === "preserver") weights.stabilite += 0.05;
  }
  Object.assign(weights, d.weights_override ?? {});
  const excluded = new Set<string>(d.base_persona ? base.pw.hard_constraints.excluded_asset_classes : []);
  const ex = d.exclusions;
  if (ex.includes("crypto")) excluded.add("crypto");
  const horizonLabel = d.base_persona ? base.horizonLabel : { court: "moins de 5 ans", moyen: "5 à 12 ans", long: "plus de 12 ans" }[d.horizon];
  const tolLabel = { faible: "faible", moderee: "modéré", elevee: "élevé" }[d.tolerance];
  return {
    tolerance: d.base_persona ? base.tolerance : d.tolerance,
    horizon: d.base_persona ? base.horizon : d.horizon,
    horizonLabel,
    speculatif: ex.includes("speculatif") ? "exclu" : base.speculatif,
    concentrationRule: base.concentrationRule || d.preferences.includes("diversification"),
    prefKey: d.base_persona ? base.prefKey : "defaut",
    pw: {
      profile_id: id,
      label: d.base_persona ? `${base.pw.label} (poids modifiés)` : "Profil fictif",
      summary: d.base_persona
        ? `${base.pw.summary} · poids modifiés`
        : `Profil fictif · risque ${tolLabel} · horizon ${horizonLabel}`,
      hard_constraints: {
        ...base.pw.hard_constraints,
        max_weight_crypto: excluded.has("crypto") ? 0 : base.pw.hard_constraints.max_weight_crypto,
        excluded_asset_classes: [...excluded],
        esg_exclusion: d.base_persona ? base.pw.hard_constraints.esg_exclusion : ex.includes("controverses"),
        speculatif: ex.includes("speculatif") ? "exclu" : base.speculatif,
      },
      weights: normalize(weights),
      rationale: [
        ...(d.weights_override ? [{ field: "weights", because: "Poids modifiés à la main sur l'écran de résumé.", claim_kind: "HYPOTHESE" as const }] : []),
        { field: "weights", because: `Gabarit de départ : niveau de risque ${tolLabel}.`, claim_kind: "HYPOTHESE" },
        ...(excluded.size ? [{ field: "hard_constraints.excluded_asset_classes", because: "Exclusions choisies dans le questionnaire.", claim_kind: "FAIT" as const }] : []),
      ],
      missing_information: d.base_persona ? base.pw.missing_information : ["Profil composé par questionnaire : aucune préférence en texte libre."],
    },
  };
}

function getMockProfile(id: string): MockProfile {
  const p = PROFILES.get(id);
  if (!p) throw new MockNotFound(`Profil ${id} introuvable`);
  return p;
}

// ---------- Moteur fictif ----------

const tickerName = (t: string) => assetByTicker(t)?.name ?? t;

function scoreOf(a: MockAsset, p: MockProfile): { contributions: CriterionMap; total: number } {
  const s: CriterionMap = { ...a.s, preferences: a.pref[p.prefKey] };
  const contributions = {} as CriterionMap;
  let total = 0;
  for (const k of CRITERIA) {
    contributions[k] = Math.round(p.pw.weights[k] * s[k] * 1000) / 1000;
    total += contributions[k];
  }
  return { contributions, total };
}

const fitOf = (score: number): Fit => (score >= 0.65 ? "élevée" : score >= 0.55 ? "partielle" : "faible");

function metricClaim(a: MockAsset, key: MetricKey, text: string): Claim {
  return { text, evidence_ids: [evId(a.ticker, key)], claim_kind: "FAIT" };
}

function weightEvidence(p: MockProfile, k: Criterion) {
  return profileEvidence(p.pw.profile_id, `weights.${k}`, `Poids du critère « ${fr.criteria[k]} » dans le profil`, Math.round(p.pw.weights[k] * 100), "%");
}

function limitEvidence(p: MockProfile, kind: "vol" | "dd") {
  const v = LIMITS[p.tolerance][kind];
  return kind === "vol"
    ? profileEvidence(p.pw.profile_id, "limite_volatilite", "Seuil indicatif de volatilité pour ce profil", v, "%")
    : profileEvidence(p.pw.profile_id, "limite_perte_max", "Seuil indicatif de perte maximale pour ce profil", -v, "%");
}

function criterionClaim(a: MockAsset, k: Criterion, p: MockProfile): Claim | null {
  switch (k) {
    case "croissance":
      return metricClaim(a, "rendement_annualise", `Rendement annualisé observé de ${fmtPct(a.m.rendement_annualise)} sur 5 ans (passé, pas une prévision).`);
    case "stabilite":
      return metricClaim(a, "volatilite", `Volatilité observée de ${fmtPct(a.m.volatilite)}, parmi les plus basses de l'univers fictif.`);
    case "horizon":
      return metricClaim(a, "pire_periode", `Pire période de 3 ans observée : ${fmtPct(a.m.pire_periode)} par an.`);
    case "diversification":
      return { text: `Secteur « ${a.sector} » distinct de la plupart des autres pistes : apport à la diversification.`, evidence_ids: [weightEvidence(p, "diversification")], claim_kind: "HYPOTHESE" };
    case "esg":
      if (a.ticker === "FNB_H") return { text: "Méthodologie d'exclusion ESG publiée par l'émetteur.", evidence_ids: [EV_ESG_H], claim_kind: "FAIT" };
      return null;
    case "preferences":
      return { text: "Correspond à une préférence déclarée dans le profil.", evidence_ids: [weightEvidence(p, "preferences")], claim_kind: "HYPOTHESE" };
    default:
      return null; // `qualite` : aucune preuve fondamentale tant qu'EDGAR n'est pas intégré
  }
}

function debateFor(a: MockAsset, p: MockProfile, score: number): DebatePosition[] {
  const lim = LIMITS[p.tolerance];
  const overVol = a.m.volatilite > lim.vol;
  const overDd = Math.abs(a.m.perte_max) > lim.dd;
  const bull: DebatePosition = {
    agent: "bull", stance: score >= 0.55 ? "appui" : "appui_reserve", confidence: "moyenne",
    arguments: [metricClaim(a, "rendement_annualise", `Rendement annualisé observé de ${fmtPct(a.m.rendement_annualise)} sur la fenêtre.`)],
    open_questions: [],
  };
  if (a.ticker === "ACTIF_G") bull.arguments.push({ text: "Lancement de produit annoncé par l'émetteur.", evidence_ids: [EV_NEWS_G], claim_kind: "FAIT" });
  const realistStance: Stance = score >= 0.65 ? "appui" : score >= 0.55 ? "appui_reserve" : "opposition";
  const top = topCriteria(scoreOf(a, p).contributions, 1)[0];
  const realist: DebatePosition = {
    agent: "realist", stance: realistStance, confidence: "moyenne",
    arguments: [
      criterionClaim(a, top, p) ?? metricClaim(a, "volatilite", `Volatilité observée de ${fmtPct(a.m.volatilite)}.`),
    ],
    open_questions: p.horizon === "long" ? ["La fenêtre de 5 ans ne couvre pas l'horizon du profil."] : [],
  };
  const bearStance: Stance = overVol || overDd || a.s.stabilite < 0.3 ? "opposition" : a.s.stabilite < 0.7 ? "appui_reserve" : "appui";
  const bear: DebatePosition = {
    agent: "bear", stance: bearStance, confidence: overVol ? "élevée" : "moyenne",
    arguments: [metricClaim(a, "perte_max", `Perte maximale observée de ${fmtPct(a.m.perte_max)} sur 5 ans.`)],
    open_questions: a.esgKnown ? [] : ["Aucune preuve ESG datée disponible."],
  };
  if (overVol) {
    bear.arguments.push({
      text: `Volatilité observée de ${fmtPct(a.m.volatilite)}, au-dessus du seuil indicatif de ${fmtPct(lim.vol, 0)} du profil.`,
      evidence_ids: [evId(a.ticker, "volatilite"), limitEvidence(p, "vol")], claim_kind: "FAIT",
    });
  }
  return [bull, realist, bear];
}

function confidenceOf(debate: DebatePosition[]): Confidence {
  const opp = debate.filter((d) => d.stance === "opposition").length;
  const res = debate.filter((d) => d.stance === "appui_reserve").length;
  if (opp >= 2) return "faible";
  if (opp === 1) return "moyenne";
  return res >= 2 ? "moyenne" : "élevée";
}

function topCriteria(c: CriterionMap, n: number): Criterion[] {
  return [...CRITERIA].sort((x, y) => c[y] - c[x]).slice(0, n);
}

interface Candidate { a: MockAsset; score: number; contributions: CriterionMap }

function constraintRejection(a: MockAsset, p: MockProfile): RejectedItem | null {
  const hc = p.pw.hard_constraints;
  if (a.asset_class === "crypto" && hc.max_weight_crypto === 0) {
    return { ticker: a.ticker, kind: "contrainte", reason: "Écarté par une règle de votre profil : part maximale en crypto de 0 %.",
      evidence_ids: [profileEvidence(p.pw.profile_id, "max_crypto", "Part maximale en crypto du profil", 0, "%")] };
  }
  if (hc.excluded_asset_classes.includes(a.asset_class)) {
    return { ticker: a.ticker, kind: "contrainte", reason: `Écarté par une règle de votre profil : classe d'actifs exclue (${fr.assetClass[a.asset_class] ?? a.asset_class}).` };
  }
  if (hc.esg_exclusion && a.controversy) {
    return { ticker: a.ticker, kind: "contrainte", reason: "Écarté par une règle de votre profil : controverse environnementale documentée.", evidence_ids: [EV_CONTROVERSE_F] };
  }
  if (p.speculatif === "exclu" && a.speculative) {
    return { ticker: a.ticker, kind: "contrainte", reason: "Écarté par une règle de votre profil : actifs hautement spéculatifs exclus.",
      evidence_ids: [evId(a.ticker, "volatilite")] };
  }
  return null;
}

function computeExplanation(runId: string, req: RunRequest): Explanation {
  const p = getMockProfile(req.profile_id);
  const rejected: RejectedItem[] = [];
  const admissible: Candidate[] = [];
  for (const a of ASSETS) {
    const r = constraintRejection(a, p);
    if (r) rejected.push(r);
    else {
      const { contributions, total } = scoreOf(a, p);
      admissible.push({ a, score: total, contributions });
    }
  }
  admissible.sort((x, y) => y.score - x.score);

  const selected: Candidate[] = [];
  const perSector = new Map<string, number>();
  const sectorCap = Math.max(1, Math.floor(p.pw.hard_constraints.max_weight_per_sector / p.pw.hard_constraints.max_weight_per_asset));
  let techCrypto = 0;
  for (const c of admissible) {
    const sector = c.a.sector ?? "—";
    // Garde-fous de concentration d'abord : un candidat bien noté mais concentrant le panier est « déclassé », avec son motif.
    if (c.score >= 0.5 && p.concentrationRule && c.a.techOrCrypto && techCrypto >= 2) {
      rejected.push({ ticker: c.a.ticker, kind: "classement",
        reason: "Déclassé pour concentration : deux pistes technologie ou crypto sont déjà retenues, et le profil souhaite éviter de miser exclusivement sur les technologies.",
        evidence_ids: [weightEvidence(p, "diversification")] });
      continue;
    }
    if (selected.length >= MAX_PISTES || c.score < 0.5) {
      rejected.push({ ticker: c.a.ticker, kind: "classement",
        reason: `Moins bien classé : adéquation calculée plus faible que les pistes retenues (critère le plus pénalisant : ${fr.criteria[weakestCriterion(c, p)]}).` });
      continue;
    }
    if ((perSector.get(sector) ?? 0) >= sectorCap) {
      rejected.push({ ticker: c.a.ticker, kind: "classement", reason: `Déclassé pour concentration : le secteur « ${sector} » a déjà atteint le plafond du profil (${fmtWeight(p.pw.hard_constraints.max_weight_per_sector)}).` });
      continue;
    }
    selected.push(c);
    perSector.set(sector, (perSector.get(sector) ?? 0) + 1);
    if (c.a.techOrCrypto) techCrypto += 1;
  }

  const items: ExplanationItem[] = selected.map((c) => buildItem(c, p));
  const allLow = items.length > 0 && items.every((i) => i.confidence === "faible");
  const noReco = items.length === 0 || allLow;
  const missing: string[] = [];
  if (items.length === 0) {
    if (admissible.length === 0) missing.push("Aucun actif de l'univers ne passe les règles du profil (classes d'actifs exclues, crypto, controverses).");
    else missing.push("Aucun actif admissible n'atteint une adéquation suffisante avec les poids du profil.");
    missing.push("Élargir l'univers ou assouplir une règle du profil changerait ce résultat.");
  } else if (allLow) {
    missing.push("Le débat est trop partagé sur toutes les pistes : la confiance est faible partout.");
  }

  const unknowns = [
    ...items.filter((i) => !assetByTicker(i.ticker)!.esgKnown).map((i) => `Aucune preuve ESG datée pour ${i.name}.`),
    "Aucune donnée fondamentale (critère « qualité ») : SEC EDGAR et SEDAR+ sont prévus, pas encore intégrés.",
    ...(p.horizon === "long" ? ["Les indicateurs décrivent 5 ans de passé : ils ne couvrent pas l'horizon du profil."] : []),
    "Poids et seuils : hypothèses de l'équipe, à calibrer.",
  ];

  const coherence = req.requested_ticker ? computeCoherence(req.requested_ticker, p, selected) : null;
  return {
    run_id: runId,
    as_of: req.as_of ?? MOCK_AS_OF,
    profile_id: req.profile_id,
    headline: noReco
      ? "Aucune piste à explorer pour ce profil"
      : `${items.length} pistes cohérentes avec votre profil, ${rejected.length} écartées`,
    no_recommendation: noReco,
    missing,
    items: noReco ? [] : items,
    rejected,
    coherence,
    unknowns,
    disclaimer: DISCLAIMER,
  };
}

function weakestCriterion(c: Candidate, p: MockProfile): Criterion {
  return [...CRITERIA].filter((k) => p.pw.weights[k] > 0)
    .sort((x, y) => (c.contributions[x] - p.pw.weights[x]) - (c.contributions[y] - p.pw.weights[y]))[0];
}

function buildItem(c: Candidate, p: MockProfile): ExplanationItem {
  const { a } = c;
  const why = topCriteria(c.contributions, CRITERIA.length)
    .map((k) => criterionClaim(a, k, p))
    .filter((x): x is Claim => x !== null)
    .slice(0, 3);
  const debate = debateFor(a, p, c.score);
  const stance = (ag: string) => fr.stance[debate.find((d) => d.agent === ag)!.stance];
  const opp = debate.some((d) => d.stance === "opposition");
  const sup = debate.some((d) => d.stance !== "opposition");
  const overVol = a.m.volatilite > LIMITS[p.tolerance].vol;
  const risks: string[] = [];
  if (a.m.volatilite > 25) risks.push("Fortes variations de prix observées sur la fenêtre.");
  if (a.asset_class === "etf_bond") risks.push("Sensibilité aux taux d'intérêt (fonds d'obligations).");
  if (a.ticker === "ACTIF_A" || a.ticker === "ACTIF_G") risks.push("Dépendance à un fournisseur partagé avec une autre société de l'univers (voir le graphe).");
  if (a.currency === "USD") risks.push("Exposition au dollar américain : les indicateurs sont convertis en CAD.");
  return {
    ticker: a.ticker, name: a.name, asset_class: a.asset_class, sector: a.sector,
    fit: fitOf(c.score),
    confidence: confidenceOf(debate),
    to_review: debate.find((d) => d.agent === "bear")!.stance === "opposition" && overVol,
    why,
    contributions: c.contributions,
    debate,
    debate_summary: { bull: stance("bull"), realist: stance("realist"), bear: stance("bear"), dissent: opp && sup },
    risks,
    limits: ["Valeurs fictives (mode développement).", "Fenêtre de 5 ans ; biais du survivant de l'univers."],
    unknowns: [
      ...(a.esgKnown ? [] : ["Aucune preuve ESG datée."]),
      "Aucune donnée fondamentale pour le critère « qualité ».",
      ...debate.flatMap((d) => d.open_questions),
    ].filter((v, i, arr) => arr.indexOf(v) === i),
  };
}

function computeCoherence(ticker: string, p: MockProfile, selected: Candidate[]): CoherenceAnalysis {
  const a = assetByTicker(ticker);
  if (!a) throw new MockNotFound(`Actif ${ticker} absent de l'univers`);
  const lim = LIMITS[p.tolerance];
  const tensions: Claim[] = [];
  let hard = false;
  const rej = constraintRejection(a, p);
  if (rej) {
    hard = true;
    tensions.push({ text: rej.reason, evidence_ids: rej.evidence_ids ?? [], claim_kind: "FAIT" });
  }
  if (a.m.volatilite > lim.vol) {
    tensions.push({
      text: `Volatilité observée de ${fmtPct(a.m.volatilite)} sur 5 ans, contre un seuil indicatif de ${fmtPct(lim.vol, 0)} pour ce profil.`,
      evidence_ids: [evId(a.ticker, "volatilite"), limitEvidence(p, "vol")], claim_kind: "FAIT",
    });
  }
  if (Math.abs(a.m.perte_max) > lim.dd) {
    tensions.push({
      text: `Perte maximale observée de ${fmtPct(a.m.perte_max)}, au-delà du seuil indicatif de ${fmtPct(-lim.dd, 0)} pour ce profil.`,
      evidence_ids: [evId(a.ticker, "perte_max"), limitEvidence(p, "dd")], claim_kind: "FAIT",
    });
  }
  if (p.horizon === "court" && a.m.pire_periode < 0) {
    tensions.push({
      text: `Sur la pire période de 3 ans observée, le rendement annualisé a été de ${fmtPct(a.m.pire_periode)} ; l'horizon de ce profil est de ${p.horizonLabel}.`,
      evidence_ids: [evId(a.ticker, "pire_periode")], claim_kind: "FAIT",
    });
  }
  if (p.speculatif === "signalé" && a.speculative) {
    tensions.push({ text: "Actif hautement spéculatif : signalé par une règle du profil.", evidence_ids: [evId(a.ticker, "volatilite")], claim_kind: "FAIT" });
  }
  const verdict: Verdict = hard || tensions.length >= 2 ? "incohérent avec le profil" : tensions.length === 1 ? "cohérent avec réserve" : "cohérent";

  const basket = selected.filter((c) => c.a.ticker !== a.ticker);
  const context: Claim[] = [];
  if (basket.length > 0) {
    const before = basket.reduce((s, c) => s + c.a.m.volatilite, 0) / basket.length;
    const after = 0.9 * before + 0.1 * a.m.volatilite;
    const evB = scenarioEvidence("panier", "Volatilité moyenne du panier simulé des pistes retenues (parts égales)", Math.round(before * 10) / 10);
    const evA = scenarioEvidence("panier", `Volatilité moyenne du panier simulé avec 10 % consacrés à ${a.ticker}`, Math.round(after * 10) / 10);
    context.push({ text: `Panier simulé des pistes retenues, à parts égales : volatilité moyenne de ${fmtPct(before)}.`, evidence_ids: [evB], claim_kind: "SCENARIO" });
    context.push({ text: `Avec 10 % consacrés à ${a.name} : volatilité moyenne de ${fmtPct(after)}.`, evidence_ids: [evA], claim_kind: "SCENARIO" });
  }
  const alternatives = basket
    .filter((c) => c.a.m.volatilite < a.m.volatilite)
    .slice(0, 2)
    .map((c) => ({
      ticker: c.a.ticker, name: c.a.name,
      why: metricClaim(c.a, "volatilite", `Volatilité observée de ${fmtPct(c.a.m.volatilite)}, pour une piste déjà cohérente avec le profil.`),
    }));
  return { ticker: a.ticker, name: a.name, verdict, tensions, context, alternatives };
}

// ---------- Runs ----------

interface MockRun { req: RunRequest; startedAt: number; result?: Explanation }
const RUNS = new Map<string, MockRun>();
let runCounter = 0;

function stepStatuses(run: MockRun): RunStatus["steps"] {
  const elapsed = Date.now() - run.startedAt;
  return RUN_STEPS.map((id, i) => {
    const start = i * STEP_MS;
    const status = elapsed >= start + STEP_MS ? "ok" : elapsed >= start ? "en_cours" : "attente";
    return { id, status };
  });
}

function findRun(id: string): MockRun {
  const run = RUNS.get(id);
  if (run) return run;
  // Après un rechargement de l'application, la mémoire du serveur fictif est vide :
  // on reconstruit le run à partir de son identifiant (mock-<profil>-<titre>-<n>).
  const m = /^mock-(.+?)-(base|[A-Z_]+)-\d+$/.exec(id);
  if (m && PROFILES.has(m[1])) {
    const rebuilt: MockRun = { req: { profile_id: m[1], requested_ticker: m[2] === "base" ? undefined : m[2] }, startedAt: 0 };
    RUNS.set(id, rebuilt);
    return rebuilt;
  }
  throw new MockNotFound(`Analyse ${id} introuvable`);
}

// ---------- Routes ----------

export const mockApi = {
  async personas(): Promise<Persona[]> {
    await sleep(150);
    return PERSONAS;
  },

  async profile(id: string): Promise<ProfileWeights> {
    await sleep(150);
    return getMockProfile(id).pw;
  },

  async createProfile(draft: ProfileDraft): Promise<ProfileWeights> {
    await sleep(500);
    // Mêmes choix acceptés que l'API (backend/easytrade/api/service.py) : le reste est refusé.
    const unknown = [
      ...draft.preferences.filter((p) => !PREFERENCES.includes(p)),
      ...draft.exclusions.filter((e) => !EXCLUSIONS.includes(e)),
    ];
    if (unknown.length) throw new MockInvalid(`Choix non pris en charge : ${unknown.join(", ")}`);
    customCounter += 1;
    const id = `${draft.base_persona ?? "fictif"}_${Date.now().toString(36)}${customCounter}`;
    const p = draftToProfile(draft, id);
    PROFILES.set(id, p);
    return p.pw;
  },

  async startRun(req: RunRequest): Promise<{ run_id: string }> {
    await sleep(200);
    getMockProfile(req.profile_id);
    if (req.requested_ticker && !assetByTicker(req.requested_ticker)) throw new MockNotFound(`Actif ${req.requested_ticker} absent de l'univers`);
    runCounter += 1;
    const run_id = `mock-${req.profile_id}-${req.requested_ticker ?? "base"}-${Date.now()}${runCounter}`;
    RUNS.set(run_id, { req, startedAt: Date.now() });
    return { run_id };
  },

  async run(id: string): Promise<RunStatus> {
    await sleep(120);
    const run = findRun(id);
    const steps = stepStatuses(run);
    const done = steps.every((s) => s.status === "ok");
    if (done && !run.result) run.result = computeExplanation(id, run.req);
    return {
      run_id: id, profile_id: run.req.profile_id, as_of: run.req.as_of ?? MOCK_AS_OF,
      requested_ticker: run.req.requested_ticker ?? null,
      status: done ? "termine" : "en_cours", steps, error: null, result: done ? run.result! : null,
    };
  },

  async trace(id: string): Promise<Trace> {
    await sleep(150);
    const run = findRun(id);
    const result = run.result ?? computeExplanation(id, run.req);
    const t0 = run.startedAt || Date.parse(`${MOCK_AS_OF}T14:00:00Z`);
    const at = (ms: number) => new Date(t0 + ms).toISOString();
    const constraintRejects = result.rejected.filter((r) => r.kind === "contrainte").length;
    const ids = (t: string) => Array.from(EVIDENCE.values()).filter((e) => e.subject === t).map((e) => e.evidence_id);
    const steps: TraceStep[] = [
      { step: "profil", kind: "llm", status: "ok", started_at: at(0), ended_at: at(820), model_id: "modèle fictif (mode développement)", prompt_version: "profile_weighting@v1", outputs: [] },
      { step: "recherche", kind: "llm", status: "ok", started_at: at(900), ended_at: at(1650), model_id: "modèle fictif (mode développement)", prompt_version: "research@v1", tools_called: ["lister_univers", "preuves_esg", "relations"], outputs: [] },
      { step: "validation", kind: "code", status: "ok", started_at: at(900), ended_at: at(1300), version: "validation@v1", outputs: ASSETS.flatMap((a) => ids(a.ticker)).slice(0, 6) },
      { step: "dossiers_de_preuves", kind: "code", status: "ok", started_at: at(1660), ended_at: at(1700), version: "engine@v1", outputs: [] },
      { step: "controle.avant_debat", kind: "controle", status: "ok", started_at: at(1700), ended_at: at(1720), note: `Contraintes dures appliquées : ${constraintRejects} candidat(s) écarté(s) par une règle du profil ; candidats sans preuve : 0.` },
      ...([1, 3] as const).flatMap((round) => (["bull", "realist", "bear"] as const).map((ag, i) => ({
        step: `debate.${ag}.round${round}`, kind: "llm" as const, status: "ok" as const, started_at: at(1800 + i * 20), ended_at: at(2600 + i * 40),
        model_id: "modèle fictif (mode développement)", prompt_version: `${ag}@v1`, tools_called: [],
      }))),
      { step: "decision", kind: "code", status: "ok", started_at: at(2700), ended_at: at(2780), version: "engine@v1", outputs: [] },
      { step: "controle.plafonds_panier", kind: "controle", status: "ok", started_at: at(2780), ended_at: at(2790),
        note: result.no_recommendation ? "Sortie « aucune recommandation » : preuves ou candidats insuffisants." : `Plafonds appliqués ; ${result.rejected.filter((r) => r.reason.startsWith("Déclassé")).length} piste(s) déclassée(s) pour concentration${result.coherence ? " ; tension profil / demande évaluée" : ""}.` },
      { step: "explication", kind: "llm", status: "ok", started_at: at(3600), ended_at: at(4400), model_id: "modèle fictif (mode développement)", prompt_version: "explanation@v1" },
      { step: "controle.avant_affichage", kind: "controle", status: "ok", started_at: at(4400), ended_at: at(4450), note: "Vérificateur de fidélité : chaque nombre correspond à une preuve citée ; 0 phrase retirée. Filtre de formulations : 0 terme refusé." },
    ];
    return { run_id: id, as_of: result.as_of, profile_id: result.profile_id, steps };
  },

  async assets(): Promise<AssetSummary[]> {
    await sleep(120);
    return ASSETS.map(({ ticker, name, asset_class, sector, currency }) => ({ ticker, name, asset_class, sector, currency }));
  },

  async asset(ticker: string, profileId?: string): Promise<AssetSheet> {
    await sleep(200);
    const a = assetByTicker(ticker);
    if (!a) throw new MockNotFound(`Actif ${ticker} absent de l'univers`);
    const p = profileId ? PROFILES.get(profileId) : undefined;
    const lim = p ? LIMITS[p.tolerance] : null;
    const range = (k: MetricKey) => {
      const vals = ASSETS.map((x) => x.m[k]);
      return { universe_min: Math.min(...vals), universe_max: Math.max(...vals) };
    };
    const metric = (k: MetricKey, label: string, window: string, profile_limit: number | null, advanced: boolean): AssetMetric => ({
      metric: k, label, value: a.m[k], unit: "%", window, evidence_id: evId(a.ticker, k), ...range(k), profile_limit, advanced,
    });
    const signals: Claim[] = [];
    if (a.ticker === "FNB_H") signals.push({ text: "Méthodologie d'exclusion ESG publiée par l'émetteur.", evidence_ids: [EV_ESG_H], claim_kind: "FAIT" });
    if (a.controversy) signals.push({ text: "Controverse environnementale documentée.", evidence_ids: [EV_CONTROVERSE_F], claim_kind: "FAIT" });
    if (a.ticker === "ACTIF_G") signals.push({ text: "Lancement de produit annoncé par l'émetteur.", evidence_ids: [EV_NEWS_G], claim_kind: "FAIT" });
    return {
      ticker: a.ticker, name: a.name, asset_class: a.asset_class, sector: a.sector, currency: a.currency, as_of: MOCK_AS_OF,
      metrics: [
        metric("volatilite", "Volatilité", "5 ans", lim ? lim.vol : null, false),
        metric("perte_max", "Perte maximale", "5 ans", lim ? -lim.dd : null, false),
        metric("pire_periode", "Pire période de 3 ans", "glissante, 3 ans", null, false),
        metric("rendement_annualise", "Rendement annualisé observé", "5 ans", null, true),
      ],
      signals,
    };
  },

  async graph(ticker: string): Promise<DependencyGraph> {
    await sleep(150);
    if (!assetByTicker(ticker)) throw new MockNotFound(`Actif ${ticker} absent de l'univers`);
    return GRAPHS[ticker] ?? { center: ticker, nodes: [{ id: ticker, label: tickerName(ticker), in_universe: true }], edges: [] };
  },

  async evidence(id: string): Promise<Evidence> {
    await sleep(100);
    const e = EVIDENCE.get(id);
    if (!e) throw new MockNotFound(`Preuve ${id} introuvable`);
    return e;
  },

  async dataOverview(): Promise<DataOverview> {
    await sleep(150);
    return { as_of: MOCK_AS_OF, sources: SOURCES, quality: QUALITY };
  },
};
