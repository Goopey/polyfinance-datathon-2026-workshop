/**
 * GET /assets, GET /assets/{ticker}, GET /assets/{ticker}/graph, GET /evidence/{id}, GET /data.
 * `GET /assets` (liste de l'univers) et `GET /data` (sources + contrôles qualité) sont des ajouts
 * proposés par le front à la table d'API de docs/01_ARCHITECTURE.md.
 */
import type { AssetSheet, AssetSummary, DataOverview, DependencyGraph, Evidence } from "../types/contracts";
import { mockApi } from "../mocks/server";
import { USE_MOCKS, http, mocked } from "./client";

const enc = encodeURIComponent;

export const listAssets = () => (USE_MOCKS ? mocked(mockApi.assets) : http.get<AssetSummary[]>("/assets"));

export const getAsset = (ticker: string, profileId?: string) =>
  USE_MOCKS
    ? mocked(() => mockApi.asset(ticker, profileId))
    : http.get<AssetSheet>(`/assets/${enc(ticker)}${profileId ? `?profile_id=${enc(profileId)}` : ""}`);

export const getGraph = (ticker: string) =>
  USE_MOCKS ? mocked(() => mockApi.graph(ticker)) : http.get<DependencyGraph>(`/assets/${enc(ticker)}/graph`);

export const getEvidence = (id: string) =>
  USE_MOCKS ? mocked(() => mockApi.evidence(id)) : http.get<Evidence>(`/evidence/${enc(id)}`);

export const getDataOverview = () => (USE_MOCKS ? mocked(mockApi.dataOverview) : http.get<DataOverview>("/data"));
