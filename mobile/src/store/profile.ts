/**
 * Profil courant et dernière analyse par profil. Persisté : on retrouve ses pistes au relancement.
 * Aucune donnée personnelle : seulement un identifiant de profil fictif.
 */
import { useEffect, useState } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { persistStorage } from "./storage";

interface ProfileState {
  profileId: string | null;
  label: string | null;
  summary: string | null;
  /** Dernier run de base (sans titre demandé) par profil. */
  runs: Record<string, string>;
  setProfile: (p: { profile_id: string; label: string; summary: string }) => void;
  setRun: (profileId: string, runId: string) => void;
  clearRun: (profileId: string) => void;
  reset: () => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profileId: null,
      label: null,
      summary: null,
      runs: {},
      setProfile: (p) => set({ profileId: p.profile_id, label: p.label, summary: p.summary }),
      setRun: (profileId, runId) => set((s) => ({ runs: { ...s.runs, [profileId]: runId } })),
      clearRun: (profileId) =>
        set((s) => {
          const runs = { ...s.runs };
          delete runs[profileId];
          return { runs };
        }),
      reset: () => set({ profileId: null, label: null, summary: null }),
    }),
    { name: "easytrade-profile", storage: persistStorage },
  ),
);

/** Vrai une fois l'état relu depuis le stockage (évite de rediriger vers l'accueil trop tôt). */
export function useProfileHydrated() {
  const [done, setDone] = useState(useProfileStore.persist.hasHydrated());
  useEffect(() => {
    const unsub = useProfileStore.persist.onFinishHydration(() => setDone(true));
    setDone(useProfileStore.persist.hasHydrated());
    return unsub;
  }, []);
  return done;
}
