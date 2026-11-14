/**
 * Analyse de base (sans titre demandé) d'un profil : réutilise le dernier run enregistré,
 * sinon en lance un. Si le run n'existe plus côté serveur (404), il est relancé.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { isNotFound } from "../api/client";
import { startRun, useRun } from "../api/runs";
import { useProfileStore } from "../store/profile";

export function useBaseRun(profileId: string | null | undefined) {
  const runId = useProfileStore((s) => (profileId ? s.runs[profileId] : undefined));
  const setRun = useProfileStore((s) => s.setRun);
  const clearRun = useProfileStore((s) => s.clearRun);
  const [startError, setStartError] = useState<unknown>(null);
  const starting = useRef<string | null>(null);

  const start = useCallback(async () => {
    if (!profileId || starting.current === profileId) return;
    starting.current = profileId;
    setStartError(null);
    try {
      const { run_id } = await startRun({ profile_id: profileId });
      setRun(profileId, run_id);
    } catch (e) {
      setStartError(e);
    } finally {
      starting.current = null;
    }
  }, [profileId, setRun]);

  useEffect(() => {
    if (profileId && !runId && !startError) void start();
  }, [profileId, runId, startError, start]);

  const query = useRun(runId);

  useEffect(() => {
    if (profileId && query.error && isNotFound(query.error)) clearRun(profileId);
  }, [query.error, profileId, clearRun]);

  const restart = useCallback(() => {
    if (!profileId) return;
    setStartError(null);
    clearRun(profileId);
  }, [profileId, clearRun]);

  return { runId, query, startError, restart };
}
