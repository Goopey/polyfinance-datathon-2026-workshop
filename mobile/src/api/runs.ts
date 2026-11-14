/**
 * POST /runs, GET /runs/{id} (interrogé périodiquement), GET /runs/{id}/trace.
 */
import { useQuery } from "@tanstack/react-query";
import type { RunRequest, RunStatus, Trace } from "../types/contracts";
import { mockApi } from "../mocks/server";
import { USE_MOCKS, http, mocked } from "./client";

export const startRun = (req: RunRequest) =>
  USE_MOCKS ? mocked(() => mockApi.startRun(req)) : http.post<{ run_id: string }>("/runs", req);

export const getRun = (id: string) =>
  USE_MOCKS ? mocked(() => mockApi.run(id)) : http.get<RunStatus>(`/runs/${encodeURIComponent(id)}`);

export const getTrace = (id: string) =>
  USE_MOCKS ? mocked(() => mockApi.trace(id)) : http.get<Trace>(`/runs/${encodeURIComponent(id)}/trace`);

/** Suit un run : interroge toutes les 700 ms tant qu'il est en cours. */
export function useRun(runId: string | null | undefined) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId!),
    enabled: !!runId,
    retry: false,
    refetchInterval: (q) => (q.state.data && q.state.data.status !== "en_cours" ? false : 700),
  });
}
