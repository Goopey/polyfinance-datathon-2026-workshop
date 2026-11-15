/**
 * Client HTTP du mobile : URL appelées, paramètre `run_id`, traduction des erreurs.
 * L'API réelle est remplacée par un faux `fetch` : on vérifie ce que le mobile envoie.
 *
 * Lancer : npm test
 */
import assert from "node:assert/strict";
import { afterEach, before, beforeEach, describe, it } from "node:test";

process.env.EXPO_PUBLIC_USE_MOCKS = "false";
process.env.EXPO_PUBLIC_API_URL = "http://api.test/";

type Call = { url: string; method: string; body: unknown };
let calls: Call[] = [];
let reply: { status: number; body: unknown } = { status: 200, body: {} };
const realFetch = globalThis.fetch;

let assets: typeof import("../src/api/assets");
let runs: typeof import("../src/api/runs");
let profiles: typeof import("../src/api/profiles");
let client: typeof import("../src/api/client");

before(async () => {
  client = await import("../src/api/client");
  assets = await import("../src/api/assets");
  runs = await import("../src/api/runs");
  profiles = await import("../src/api/profiles");
});

beforeEach(() => {
  calls = [];
  reply = { status: 200, body: {} };
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), method: init?.method ?? "GET", body: init?.body ? JSON.parse(String(init.body)) : undefined });
    return new Response(JSON.stringify(reply.body), { status: reply.status, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("client HTTP (EXPO_PUBLIC_USE_MOCKS=false)", () => {
  it("lit la configuration et retire la barre finale de l'URL", () => {
    assert.equal(client.USE_MOCKS, false);
    assert.equal(client.API_URL, "http://api.test");
  });

  it("les preuves, fiches et graphes sont demandés pour le run consulté", async () => {
    await assets.getEvidence("EV-000412", "run_2026-11-12_robert_TSLA");
    await assets.getAsset("XIU.TO", { profileId: "robert", runId: "run_2026-11-12_robert" });
    await assets.getGraph("BTC-USD", "run_2026-11-12_amira");
    await assets.getPrices("RY.TO", "run_2026-11-12_robert");
    await assets.getDataOverview("run_2026-11-12_amira");
    assert.deepEqual(calls.map((c) => c.url), [
      "http://api.test/evidence/EV-000412?run_id=run_2026-11-12_robert_TSLA",
      "http://api.test/assets/XIU.TO?profile_id=robert&run_id=run_2026-11-12_robert",
      "http://api.test/assets/BTC-USD/graph?run_id=run_2026-11-12_amira",
      "http://api.test/assets/RY.TO/prices?run_id=run_2026-11-12_robert",
      "http://api.test/data?run_id=run_2026-11-12_amira",
    ]);
  });

  it("sans run, aucun paramètre vide n'est envoyé", async () => {
    await assets.getEvidence("EV-000001");
    await assets.getAsset("AAPL");
    await assets.getGraph("AAPL", null);
    await assets.getDataOverview(undefined);
    assert.deepEqual(calls.map((c) => c.url), [
      "http://api.test/evidence/EV-000001", "http://api.test/assets/AAPL", "http://api.test/assets/AAPL/graph", "http://api.test/data",
    ]);
  });

  it("POST /runs et POST /profiles envoient le corps attendu", async () => {
    await runs.startRun({ profile_id: "robert", requested_ticker: "TSLA" });
    await profiles.createProfile({ objectif: "preserver", horizon: "court", tolerance: "faible", preferences: [], exclusions: ["crypto"] });
    await runs.getRun("run_2026-11-12_robert_TSLA");
    await runs.getTrace("run_2026-11-12_robert_TSLA");
    await profiles.getProfile("fictif_0c554e1c");
    assert.deepEqual(calls.map((c) => `${c.method} ${c.url}`), [
      "POST http://api.test/runs", "POST http://api.test/profiles", "GET http://api.test/runs/run_2026-11-12_robert_TSLA",
      "GET http://api.test/runs/run_2026-11-12_robert_TSLA/trace", "GET http://api.test/profiles/fictif_0c554e1c",
    ]);
    assert.deepEqual(calls[0].body, { profile_id: "robert", requested_ticker: "TSLA" });
    assert.deepEqual(calls[1].body, { objectif: "preserver", horizon: "court", tolerance: "faible", preferences: [], exclusions: ["crypto"] });
  });

  it("une réponse 404 devient une ApiError « introuvable » avec le détail du serveur", async () => {
    reply = { status: 404, body: { detail: "Analyse inconnue : run_x" } };
    await assert.rejects(runs.getRun("run_x"), (e: unknown) => {
      assert.ok(e instanceof client.ApiError);
      const error = e as InstanceType<typeof client.ApiError>;
      assert.equal(error.status, 404);
      assert.equal(error.message, "Analyse inconnue : run_x");
      assert.ok(client.isNotFound(e));
      return true;
    });
  });

  it("une API injoignable donne un message qui nomme l'URL configurée", async () => {
    globalThis.fetch = (async () => {
      throw new TypeError("fetch failed");
    }) as typeof fetch;
    await assert.rejects(assets.listAssets(), /API injoignable \(http:\/\/api\.test\)/);
  });
});
