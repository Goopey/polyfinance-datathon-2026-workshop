/**
 * Préférences d'affichage : mode Simple (défaut) ou Avancé (docs/07_UX_UI.md, principe 4),
 * et langue de l'interface (français par défaut, anglais).
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { persistStorage } from "./storage";

export type ReadingMode = "simple" | "avance";
export type Lang = "fr" | "en";

interface SettingsState {
  mode: ReadingMode;
  lang: Lang;
  setMode: (m: ReadingMode) => void;
  setLang: (l: Lang) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      mode: "simple",
      lang: "fr",
      setMode: (mode) => set({ mode }),
      setLang: (lang) => set({ lang }),
    }),
    { name: "easytrade-settings", storage: persistStorage },
  ),
);
