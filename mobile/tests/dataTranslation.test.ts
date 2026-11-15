/**
 * Traduction des textes du backend (src/i18n/data.ts).
 *
 * Corpus : tests/fixtures/backend_strings.json, collecté sur l'API réelle par
 * scripts/harvest_backend_strings.py (personas, profils du questionnaire, analyses des 3 personas,
 * 93 « Tester une idée », traces, fiches, graphes, preuves, écran Données).
 * Chaque chaîne doit avoir une traduction anglaise, sans reste de français.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { enNumbers, translateData, translateToEnglish } from "../src/i18n/translate";

const here = dirname(fileURLToPath(import.meta.url));
const corpus: { text: string; paths: string[] }[] = JSON.parse(readFileSync(join(here, "fixtures", "backend_strings.json"), "utf8"));

/** Chaînes neutres (noms propres, identifiants) : identiques dans les deux langues. */
const NEUTRAL = /^(?:[A-Z0-9.\-]+|[A-Z][\w&'.,()\- /]*(?:ETF|Trust|Fund|Inc\.?|Corp\.?|Bank|Gold Shares|Ether|Bitcoin)[\w&'.,()\- /]*)$/;

/** Champs que l'application n'affiche pas (ou affiche par clé, via le dictionnaire de l'interface). */
const NOT_DISPLAYED = [
  /^personas\[\]\.profil\.(nom|profession|situation|experience|test|tolerance_risque)$/,
  /^run\.result\.disclaimer$/, /^run\.result\.items\[\]\.debate_summary\./, /^trace\.steps\[\]\.(inputs|version)/,
  /^assets\[\]\.name$/, /^sheet\.sentiment\.label$/,
];

/** Noms propres (sociétés, personas) : jamais traduits. */
const PROPER_NAMES = [/^assets\[\]\.name$/, /^personas\[\]\.profil\.nom$/];

/** Indices de français restant après traduction. */
const FRENCH = /[àâçéèêëîïôûùüÿœ]|\b(?:le|la|les|des|du|une|est|sont|pour|avec|sans|sur|dans|aucun|aucune|pas|selon|votre|vos|ou|et)\b/i;

/** Mots anglais légitimes contenant des accents (noms propres, emprunts) ou mots courts ambigus. */
const ALLOWED_ACCENTED = /Couche-Tard|Alimentation|Québec|Montréal|Finnhub|yfinance|Yahoo/;

describe("traduction des textes du backend", () => {
  it("le corpus collecté sur l'API n'est pas vide", () => {
    assert.ok(corpus.length > 200, `corpus de ${corpus.length} chaînes`);
  });

  it("chaque chaîne a une traduction anglaise complète", () => {
    const missing: string[] = [];
    const leftovers: string[] = [];
    for (const { text, paths } of corpus) {
      if (paths.every((p) => NOT_DISPLAYED.some((re) => re.test(p)))) continue;
      if (paths.some((p) => PROPER_NAMES.some((re) => re.test(p)))) continue; // noms propres : identiques en anglais
      const en = translateToEnglish(text);
      if (en === null) {
        if (!NEUTRAL.test(text.trim())) missing.push(`${text}   ← ${paths[0]}`);
        continue;
      }
      const probe = en.replace(ALLOWED_ACCENTED, "");
      if (FRENCH.test(probe)) leftovers.push(`${text}\n   → ${en}`);
    }
    assert.deepEqual(missing, [], `${missing.length} chaîne(s) sans traduction :\n${missing.slice(0, 40).join("\n")}`);
    assert.deepEqual(leftovers, [], `${leftovers.length} traduction(s) avec du français :\n${leftovers.slice(0, 30).join("\n")}`);
  });

  it("les nombres passent au format anglais", () => {
    assert.equal(enNumbers("13,1 % et -6,3 %"), "13.1% et -6.3%");
    assert.equal(enNumbers("1 234,5 CAD"), "1,234.5 CAD");
    assert.equal(enNumbers("le 2026-11-12, EV-000412"), "le 2026-11-12, EV-000412");
  });

  it("français : secteurs traduits, « fictif » jamais affiché", () => {
    assert.equal(translateData("Financials", "fr"), "Finance");
    assert.equal(translateData("Profil fictif", "fr"), "Mon profil");
    assert.equal(translateData("Profil fictif", "en"), "My profile");
  });

  it("une chaîne inconnue est rendue telle quelle", () => {
    assert.equal(translateData("Texte libre d'un modèle.", "en"), "Texte libre d'un modèle.");
  });
});
