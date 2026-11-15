/**
 * Contrat mobile ↔ backend, côté mobile.
 *
 * 1. `contracts.schema.json` est à jour par rapport à `src/types/contracts.ts`.
 * 2. Chaque route du serveur fictif rend une réponse conforme à ce schéma : le mode « données
 *    fictives » et l'API réelle (testée par backend/tests/api/ contre le même schéma) sont donc
 *    interchangeables pour l'interface.
 * 3. Règles d'affichage tenues par les données fictives : aucune formulation refusée, aucune
 *    affirmation sans preuve existante, aucune preuve publiée après la date d'analyse.
 *
 * Lancer : npm test
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { before, describe, it } from "node:test";
import Ajv, { type ValidateFunction } from "ajv";

process.env.EXPO_PUBLIC_MOCK_STEP_MS = "5"; // avant l'import du serveur fictif

const ROOT = resolve(import.meta.dirname, "..");
const schemaText = readFileSync(resolve(ROOT, "contracts.schema.json"), "utf8").replace(/\r\n/g, "\n");
const schema = JSON.parse(schemaText);
const ajv = new Ajv({ allErrors: true, strict: false });
ajv.addSchema(schema, "contracts");

const validators = new Map<string, ValidateFunction>();
function conforms(type: string, value: unknown, label = type) {
  let validate = validators.get(type);
  if (!validate) {
    assert.ok(schema.definitions[type], `type absent du schéma : ${type}`);
    validate = ajv.compile({ $ref: `contracts#/definitions/${type}` });
    validators.set(type, validate);
  }
  const ok = validate(JSON.parse(JSON.stringify(value)));
  assert.ok(ok, `${label} non conforme à ${type} : ${ajv.errorsText(validate.errors, { separator: "\n  " })}`);
}

type Server = typeof import("../src/mocks/server");
let server: Server;
let api: Server["mockApi"];

async function finishedRun(profile_id: string, requested_ticker?: string) {
  const { run_id } = await api.startRun({ profile_id, requested_ticker });
  for (let i = 0; i < 400; i++) {
    const status = await api.run(run_id);
    if (status.status !== "en_cours") return status;
  }
  throw new Error(`run ${run_id} non terminé`);
}

function evidenceIds(value: unknown): string[] {
  const ids = new Set<string>();
  JSON.stringify(value, (key, v) => {
    if (key === "evidence_ids" && Array.isArray(v)) v.forEach((id: string) => ids.add(id));
    if (key === "evidence_id" && typeof v === "string") ids.add(v);
    return v;
  });
  return [...ids];
}

before(async () => {
  server = await import("../src/mocks/server");
  api = server.mockApi;
});

describe("schéma des contrats", () => {
  it("contracts.schema.json est à jour par rapport à contracts.ts", async () => {
    const { buildSchema } = await import("../scripts/contracts-schema.mjs");
    assert.equal(schemaText, buildSchema(), "lancer `npm run contracts` puis relancer les tests des deux côtés");
  });

  it("les types servis par l'API sont tous dans le schéma", () => {
    for (const type of ["Persona", "ProfileWeights", "ProfileDraft", "RunRequest", "RunStatus", "Explanation", "Trace",
      "AssetSummary", "AssetSheet", "DependencyGraph", "Evidence", "DataOverview"]) {
      assert.ok(schema.definitions[type], type);
    }
  });
});

describe("serveur fictif conforme au contrat", () => {
  it("GET /personas, GET /profiles/{id}", async () => {
    const personas = await api.personas();
    assert.equal(personas.length, 3);
    for (const p of personas) {
      conforms("Persona", p, `persona ${p.id}`);
      conforms("ProfileWeights", await api.profile(p.id), `profil ${p.id}`);
    }
  });

  it("POST /profiles : questionnaire et poids modifiés", async () => {
    const draft = { objectif: "preserver", horizon: "court", tolerance: "faible", preferences: ["esg"], exclusions: ["crypto", "speculatif"] } as const;
    conforms("ProfileDraft", draft);
    const created = await api.createProfile({ ...draft, preferences: [...draft.preferences], exclusions: [...draft.exclusions] });
    conforms("ProfileWeights", created);
    assert.equal(created.hard_constraints.max_weight_crypto, 0);
    assert.equal(created.hard_constraints.speculatif, "exclu");
    const variant = await api.createProfile({
      base_persona: "amira", objectif: "equilibre", horizon: "moyen", tolerance: "moderee", preferences: [], exclusions: [],
      weights_override: { esg: 0.6 },
    });
    conforms("ProfileWeights", variant);
    const total = Object.values(variant.weights).reduce((a, b) => a + b, 0);
    assert.ok(Math.abs(total - 1) < 0.01, `somme des poids = ${total}`);
  });

  it("POST /profiles refuse un choix que le moteur n'applique pas", async () => {
    await assert.rejects(
      api.createProfile({ objectif: "equilibre", horizon: "moyen", tolerance: "moderee", preferences: [], exclusions: ["actions"] }),
      server.MockInvalid,
    );
  });

  it("POST /runs, GET /runs/{id} : en cours puis terminé, pour les trois personas", async () => {
    const { run_id } = await api.startRun({ profile_id: "amira" });
    conforms("RunStatus", await api.run(run_id), "run en cours");
    for (const persona of ["amira", "mateo", "robert"]) {
      const status = await finishedRun(persona);
      assert.equal(status.status, "termine");
      conforms("RunStatus", status, `run ${persona}`);
      conforms("Trace", await api.trace(status.run_id), `trace ${persona}`);
    }
  });

  it("« Tester une idée » : analyse de cohérence présente et conforme", async () => {
    const status = await finishedRun("robert", "ACTIF_G");
    conforms("RunStatus", status);
    assert.equal(status.result?.coherence?.verdict, "incohérent avec le profil");
    assert.ok((status.result?.coherence?.tensions.length ?? 0) > 0);
  });

  it("GET /assets, /assets/{ticker}, /assets/{ticker}/graph, /data", async () => {
    const assets = await api.assets();
    for (const a of assets) {
      conforms("AssetSummary", a);
      conforms("AssetSheet", await api.asset(a.ticker, "robert"), `fiche ${a.ticker}`);
      conforms("DependencyGraph", await api.graph(a.ticker), `graphe ${a.ticker}`);
    }
    conforms("DataOverview", await api.dataOverview());
  });

  it("titre ou profil inconnu : erreur « introuvable »", async () => {
    await assert.rejects(api.startRun({ profile_id: "inconnu" }), server.MockNotFound);
    await assert.rejects(api.startRun({ profile_id: "amira", requested_ticker: "NOPE" }), server.MockNotFound);
    await assert.rejects(api.evidence("EV-INCONNUE"), server.MockNotFound);
  });
});

describe("règles d'affichage sur les données fictives", () => {
  const forbidden = readFileSync(resolve(ROOT, "../data/reference/forbidden_wording.txt"), "utf8")
    .split(/\r?\n/).map((l) => l.trim().toLowerCase()).filter((l) => l && !l.startsWith("#"));

  it("aucune formulation refusée, toute preuve citée existe et n'est pas postérieure à l'analyse", async () => {
    assert.ok(forbidden.includes("achetez") && forbidden.includes("garanti"));
    const runs = [await finishedRun("amira"), await finishedRun("mateo"), await finishedRun("robert"), await finishedRun("robert", "ACTIF_G")];
    for (const status of runs) {
      const outputs = [status.result, await api.trace(status.run_id)];
      const text = JSON.stringify(outputs).toLowerCase();
      assert.deepEqual(forbidden.filter((term) => text.includes(term)), [], status.run_id);
      assert.match(status.result!.disclaimer, /Simulation/);
      for (const id of evidenceIds(status.result)) {
        const evidence = await api.evidence(id);
        conforms("Evidence", evidence, id);
        assert.ok(evidence.published_at <= status.as_of, `${id} publiée après ${status.as_of}`);
      }
    }
  });

  it("chaque affirmation d'une piste cite au moins une preuve", async () => {
    const status = await finishedRun("amira");
    for (const item of status.result!.items) {
      for (const claim of [...item.why, ...item.debate.flatMap((d) => d.arguments)]) {
        assert.ok(claim.evidence_ids.length > 0, `${item.ticker} : « ${claim.text} » sans preuve`);
      }
    }
  });

  it("une arête du graphe porte une preuve ou l'étiquette Hypothèse (S10)", async () => {
    for (const a of await api.assets()) {
      for (const edge of (await api.graph(a.ticker)).edges) {
        assert.ok(edge.evidence_id || edge.claim_kind === "HYPOTHESE", `${edge.source} → ${edge.target}`);
      }
    }
  });
});

describe("exemples et garde-fou", () => {
  it("les fichiers d'exemple de src/mocks/ respectent le contrat", () => {
    for (const [file, type] of [["explanation", "Explanation"], ["evidence", "Evidence"], ["graph", "DependencyGraph"]]) {
      const { _avertissement, ...example } = JSON.parse(readFileSync(resolve(ROOT, `src/mocks/${file}.exemple.json`), "utf8"));
      assert.ok(_avertissement, `${file} : avertissement « données fictives » absent`);
      conforms(type, example, `${file}.exemple.json`);
    }
  });

  it("le validateur refuse un champ en trop, un champ manquant et une valeur hors énumération", async () => {
    const good = JSON.parse(JSON.stringify(await finishedRun("amira")));
    conforms("RunStatus", good);
    const { steps, ...missing } = good;
    const wrong = JSON.parse(JSON.stringify(good));
    wrong.result.items[0].confidence = "élevé"; // forme du moteur ; le contrat attend « élevée »
    for (const bad of [{ ...good, champ_hors_contrat: 1 }, missing, wrong]) {
      assert.throws(() => conforms("RunStatus", bad), /non conforme/);
    }
    assert.ok(steps);
  });
});
