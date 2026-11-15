/**
 * GET /assets, GET /assets/{ticker}, GET /assets/{ticker}/graph, GET /evidence/{id}, GET /data.
 *
 * `runId` : les identifiants de preuves sont propres à une analyse (`EV-000412` ne désigne pas la
 * même preuve dans deux runs). La fiche, le graphe et la preuve sont donc demandés pour le run
 * consulté ; sans run, l'API répond depuis son registre « hors analyse ».
 */
import type { AssetSheet, AssetSummary, DataOverview, DependencyGraph, Evidence } from "../types/contracts";
import { mockApi } from "../mocks/server";
import { USE_MOCKS, http, mocked } from "./client";

const enc = encodeURIComponent;

/** Chaîne de requête sans les paramètres absents. */
export function query(params: Record<string, string | null | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${enc(v as string)}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export const listAssets = () => (USE_MOCKS ? mocked(mockApi.assets) : http.get<AssetSummary[]>("/assets"));

export const getAsset = (ticker: string, opts: { profileId?: string | null; runId?: string | null } = {}) =>
  USE_MOCKS
    ? mocked(() => mockApi.asset(ticker, opts.profileId ?? undefined))
    : http.get<AssetSheet>(`/assets/${enc(ticker)}${query({ profile_id: opts.profileId, run_id: opts.runId })}`);

export const getGraph = (ticker: string, runId?: string | null) =>
  USE_MOCKS
    ? mocked(() => mockApi.graph(ticker))
    : http.get<DependencyGraph>(`/assets/${enc(ticker)}/graph${query({ run_id: runId })}`);

export const getEvidence = (id: string, runId?: string | null) =>
  USE_MOCKS ? mocked(() => mockApi.evidence(id)) : http.get<Evidence>(`/evidence/${enc(id)}${query({ run_id: runId })}`);

export const getDataOverview = (runId?: string | null) =>
  USE_MOCKS ? mocked(mockApi.dataOverview) : http.get<DataOverview>(`/data${query({ run_id: runId })}`);
