/**
 * Traduction des textes produits par le backend (agents, moteur, registre de preuves) — fonctions pures.
 *
 * Le backend rédige en français ; l'interface doit pourtant être entièrement en anglais quand
 * l'utilisateur choisit EN. Ces textes sont produits par des gabarits (agents simulés, moteur de
 * décision, registre) : on les traduit par règles (texte exact, puis motifs dont les chiffres sont
 * repris tels quels et remis au format anglais).
 *
 * - Couverture vérifiée par tests/dataTranslation.test.ts sur un corpus collecté sur l'API réelle
 *   (tests/fixtures/backend_strings.json) : toute chaîne non couverte fait échouer le test.
 * - Texte libre rédigé par un vrai modèle (raisons, débat, motifs du profil) : aucune règle ne peut le
 *   prévoir. Le backend joint à chaque résultat sa version anglaise (`translations`, étape de traduction
 *   de backend/easytrade/agents/translation.py) ; l'API l'enregistre ici (`registerTranslations`) et elle
 *   sert quand les règles ne couvrent pas la phrase.
 * - Une chaîne inconnue des règles et de ces tables est affichée telle quelle.
 * - Sens inverse : quelques données arrivent en anglais (secteurs) ; en français, on les traduit.
 * - En français, le libellé interne « Profil fictif » (profil du questionnaire) devient « Mon profil ».
 * Le crochet React `useTx()` est dans data.ts.
 */
import { EN_EXACT, EN_RULES, FR_EXACT, FR_RULES, type Rule } from "./dataRules";

export type Lang = "fr" | "en";

/** Nombre au format français (« 1 234,5 », « -6,3 ») → anglais (« 1,234.5 », « -6.3 »). */
export function enNumber(s: string): string {
  const clean = s.replace(/[   ]/g, "");
  const [int, dec] = clean.split(",");
  const sign = /^[-−]/.test(int) ? "-" : int.startsWith("+") ? "+" : "";
  const digits = int.replace(/^[-−+]/, "");
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${sign}${grouped}${dec !== undefined ? `.${dec}` : ""}`;
}

/** Après traduction : « 13,1 % » → « 13.1% », « 1 234,5 » → « 1,234.5 » (dates ISO et identifiants intacts). */
export function enNumbers(s: string): string {
  return s
    .replace(/(^|[^\d\w-])([-−+]?\d{1,3}(?:[   ]\d{3})+(?:,\d+)?|[-−+]?\d+,\d+)(?![\d\w])/g,
      (_m, pre: string, num: string) => `${pre}${enNumber(num)}`)
    .replace(/(\d)[   ]%/g, "$1%");
}

function applyRules(s: string, exact: Record<string, string>, rules: Rule[]): string | null {
  const hit = exact[s];
  if (hit !== undefined) return hit;
  for (const [re, out] of rules) {
    const m = re.exec(s);
    if (m) return typeof out === "string" ? s.replace(re, out) : out(...(m as unknown as string[]));
  }
  return null;
}

const SPLITS: { re: RegExp; join: string; keep?: string }[] = [
  { re: /\.\s+(?=[A-ZÀ-Ý«(])/, join: " ", keep: "." },
  { re: /\s+;\s+/, join: "; " },
  { re: /\s+—\s+/, join: " — " },
  { re: /\s+·\s+/, join: " · " },
];

/**
 * Traduit une phrase entière, sinon morceau par morceau (phrases séparées par « . », « ; », « — » ou « · »).
 * Rend `null` si une partie n'est pas couverte (le test de couverture s'en sert).
 */
export function translateToEnglish(input: string): string | null {
  const s = input.trim().replace(/\u2019/g, "'"); // apostrophe typographique = apostrophe droite
  if (!s) return input;
  const whole = applyRules(s, EN_EXACT, EN_RULES);
  if (whole !== null) return enNumbers(whole);
  for (const { re, join, keep } of SPLITS) {
    let parts = s.split(re);
    if (parts.length > 1) {
      if (keep) parts = parts.map((p, i) => (i < parts.length - 1 ? `${p}${keep}` : p));
      const out = parts.map(translateToEnglish);
      if (out.every((p) => p !== null)) return out.join(join);
    }
  }
  return null;
}

/** Version anglaise du texte rédigé par les modèles, reçue avec les résultats (français → anglais). */
const fromResults = new Map<string, string>();

export function registerTranslations(table: Record<string, string> | null | undefined): void {
  if (!table) return;
  for (const [fr, en] of Object.entries(table)) if (fr && en) fromResults.set(fr.trim(), en);
}

export function translateData(text: string, lang: Lang): string {
  if (!text) return text;
  if (lang === "fr") return applyRules(text.trim(), FR_EXACT, FR_RULES) ?? text;
  return translateToEnglish(text) ?? fromResults.get(text.trim()) ?? text;
}
