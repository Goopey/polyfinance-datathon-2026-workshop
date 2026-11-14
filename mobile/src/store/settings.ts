/**
 * Préférences d'affichage : mode Simple (défaut) ou Avancé. Conception : docs/07_UX_UI.md (principe 4).
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { persistStorage } from "./storage";

export type ReadingMode = "simple" | "avance";

interface SettingsState {
  mode: ReadingMode;
  setMode: (m: ReadingMode) => void;
}

export const useSettings = create<SettingsState>()(
  persist((set) => ({ mode: "simple", setMode: (mode) => set({ mode }) }), {
    name: "easytrade-settings",
    storage: persistStorage,
  }),
);
