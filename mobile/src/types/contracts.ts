/**
 * Types TypeScript des contrats JSON (miroir des schémas Pydantic de backend/easytrade/schemas/).
 *
 * - `Evidence` reprend exactement backend/easytrade/schemas/evidence.py (P1, implémenté).
 * - Les autres types suivent docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md et docs/05_EXPLICABILITE.md.
 *   Les schémas Pydantic correspondants (P2, P3) ne sont pas encore écrits : les champs marqués
 *   « proposé (P5) » sont la proposition du front, à reprendre tels quels ou à aligner côté backend.
 */

// ---------- Transverse ----------

export type ClaimKind = "FAIT" | "HYPOTHESE" | "SCENARIO";
export type EvidenceType = "metric" | "filing" | "esg" | "relation" | "macro" | "news" | "profile";

export const CRITERIA = [
  "croissance", "stabilite", "diversification", "esg", "qualite", "horizon", "preferences",
] as const;
export type Criterion = (typeof CRITERIA)[number];
export type CriterionMap = Record<Criterion, number>;

// ---------- Preuves (schemas/evidence.py) ----------

export interface EvidenceWindow {
  start: string | null;
  end: string | null;
  observations: number | null;
}

export interface EvidenceSource {
  source_id: string;
  name: string;
  url: string | null;
}

export interface Evidence {
  evidence_id: string;
  type: EvidenceType;
  claim_kind: ClaimKind;
  subject: string;
  statement: string;
  value: number | null;
  unit: string | null;
  currency: string | null;
  window: EvidenceWindow;
  observed_at: string;
  published_at: string;
  retrieved_at: string | null;
  source: EvidenceSource;
  processing: string;
  produced_by: string;
  limits: string;
}

/** Affirmation courte, toujours rattachée à au moins une preuve. */
export interface Claim {
  text: string;
  evidence_ids: string[];
  claim_kind: ClaimKind;
}

// ---------- Profil ----------

/** Entrée de data/reference/personas.json. */
export interface Persona {
  id: string;
  profil: {
    nom: string;
    age: number;
    profession: string;
    situation: string;
    experience: string;
    tolerance_risque: string;
    horizon_annees: { min: number; max: number | null };
    objectif: string;
    preferences: string[];
    test: string;
  };
  poids: CriterionMap;
  contraintes: PersonaConstraints;
}

export interface PersonaConstraints {
  max_weight_per_asset: number;
  max_weight_per_sector: number;
  max_weight_crypto: number;
  esg_exclusion: boolean;
  speculatif: "permis" | "exclu" | "signalé";
}

/** Réponses du questionnaire « Créer un profil fictif » (proposé P5, corps de POST /profiles). */
export interface ProfileDraft {
  objectif: "preserver" | "equilibre" | "croissance";
  horizon: "court" | "moyen" | "long";
  tolerance: "faible" | "moderee" | "elevee";
  preferences: string[];
  exclusions: string[];
  /** Poids modifiés par l'utilisateur sur l'écran de résumé ; normalisés par le backend. */
  weights_override?: Partial<CriterionMap>;
}

/** Sortie de l'agent de pondération (docs/02_AGENTS.md §1). */
export interface ProfileWeights {
  profile_id: string;
  label: string; // proposé (P5) : nom affiché (« Amira » ou « Profil fictif »)
  summary: string; // proposé (P5) : rappel du profil en une ligne
  hard_constraints: {
    max_weight_per_asset: number;
    max_weight_per_sector: number;
    max_weight_crypto: number;
    excluded_asset_classes: string[];
    esg_exclusion: boolean;
  };
  weights: CriterionMap;
  rationale: { field: string; because: string; claim_kind?: ClaimKind }[];
  missing_information: string[];
}

// ---------- Exécution d'une analyse ----------

export type RunStepId = "profil" | "recherche_validation" | "debat" | "decision" | "explication";
export const RUN_STEPS: RunStepId[] = ["profil", "recherche_validation", "debat", "decision", "explication"];
export type StepStatus = "attente" | "en_cours" | "ok" | "echec";

export interface RunRequest {
  profile_id: string;
  as_of?: string;
  requested_ticker?: string;
}

/** Réponse de GET /runs/{id}. */
export interface RunStatus {
  run_id: string;
  profile_id: string;
  as_of: string;
  requested_ticker: string | null;
  status: "en_cours" | "termine" | "echec";
  steps: { id: RunStepId; status: StepStatus }[];
  error: string | null;
  result: Explanation | null;
}

// ---------- Débat ----------

export type Stance = "appui" | "appui_reserve" | "opposition";
export type Confidence = "élevée" | "moyenne" | "faible";
export type DebateAgent = "bull" | "realist" | "bear";

/** Position finale d'un agent (tour 3), docs/02_AGENTS.md §3. */
export interface DebatePosition {
  agent: DebateAgent;
  stance: Stance;
  confidence: Confidence;
  arguments: Claim[];
  open_questions: string[];
}

// ---------- Explication (sortie finale) ----------

export type Fit = "élevée" | "partielle" | "faible";

export interface ExplanationItem {
  ticker: string;
  name: string;
  asset_class: string;
  sector: string | null; // proposé (P5)
  fit: Fit;
  confidence: Confidence;
  to_review: boolean; // proposé (P5) : drapeau « à examiner » (opposition du Bear liée à une contrainte)
  why: Claim[];
  contributions: CriterionMap;
  debate: DebatePosition[]; // proposé (P5) : positions complètes pour la fiche
  debate_summary: { bull: string; realist: string; bear: string; dissent: boolean };
  risks: string[];
  limits: string[];
  unknowns: string[]; // proposé (P5)
}

export interface RejectedItem {
  ticker: string;
  reason: string;
  kind: "contrainte" | "classement" | "preuves"; // proposé (P5) : écarté par une règle / moins bien classé / preuves manquantes
  evidence_ids?: string[];
}

export type Verdict = "cohérent" | "cohérent avec réserve" | "incohérent avec le profil";

/** Analyse de cohérence de « Tester une idée » (docs/03_DECISION_ENGINE.md). */
export interface CoherenceAnalysis {
  ticker: string;
  name: string;
  verdict: Verdict;
  tensions: Claim[];
  context: Claim[]; // effet sur le panier simulé (SCENARIO)
  alternatives: { ticker: string; name: string; why: Claim }[];
}

export interface Explanation {
  run_id: string;
  as_of: string;
  profile_id: string;
  headline: string;
  no_recommendation: boolean; // proposé (P5)
  missing: string[]; // proposé (P5) : ce qui manque quand no_recommendation est vrai
  items: ExplanationItem[];
  rejected: RejectedItem[];
  coherence: CoherenceAnalysis | null; // présent si requested_ticker
  unknowns: string[];
  disclaimer: string;
}

// ---------- Trace (docs/05_EXPLICABILITE.md §3) ----------

export interface TraceStep {
  step: string;
  kind: "code" | "llm" | "controle";
  status: "ok" | "echec" | "ignore";
  started_at: string;
  ended_at: string;
  model_id?: string | null;
  prompt_version?: string | null;
  version?: string | null;
  tools_called?: string[];
  outputs?: string[];
  note?: string; // résultat d'un contrôle de gouvernance
}

export interface Trace {
  run_id: string;
  as_of: string;
  profile_id: string;
  steps: TraceStep[];
}

// ---------- Fiche d'un actif ----------

export interface AssetSummary {
  ticker: string;
  name: string;
  asset_class: string;
  sector: string | null;
  currency: string;
}

export interface AssetMetric {
  metric: "rendement_annualise" | "volatilite" | "perte_max" | "pire_periode" | string;
  label: string;
  value: number;
  unit: string;
  window: string;
  evidence_id: string;
  universe_min: number; // proposé (P5) : bornes de l'univers à la même date, pour situer la valeur
  universe_max: number;
  profile_limit: number | null; // proposé (P5) : seuil indicatif tiré du profil (HYPOTHESE de l'équipe)
  advanced: boolean; // affiché seulement en mode Avancé
}

export interface AssetSheet extends AssetSummary {
  as_of: string;
  metrics: AssetMetric[];
  signals: Claim[]; // ESG, nouvelles datées
}

// ---------- Graphe (docs/04_DONNEES.md §6) ----------

export type Relation = "FOURNISSEUR" | "CLIENT" | "CONCURRENT" | "PARTENAIRE";

export interface GraphNode {
  id: string;
  label: string;
  in_universe: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: Relation;
  claim_kind: "FAIT" | "HYPOTHESE";
  evidence_id: string | null;
}

export interface DependencyGraph {
  center: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---------- Données (écran « Données ») ----------

export interface SourceInfo {
  source_id: string;
  nom: string;
  type_de_donnee: string;
  date_extraction: string | null;
  limites: string;
  statut: string;
}

export interface QualityCheck {
  check: string;
  status: "ok" | "avertissement" | "erreur";
  details: string[];
}

export interface DataOverview {
  as_of: string;
  sources: SourceInfo[];
  quality: QualityCheck[];
}
