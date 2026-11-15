/**
 * `useTx()` : textes du backend dans la langue de l'interface (règles : translate.ts, dataRules.ts).
 */
import { useCallback } from "react";
import { useSettings } from "../store/settings";
import { translateData } from "./translate";

export { translateData } from "./translate";

export function useTx(): (text: string) => string {
  const lang = useSettings((s) => s.lang);
  return useCallback((text: string) => translateData(text, lang), [lang]);
}

/**
 * Identifiant interne → nom lisible : « fictif_700416db » → « Mon profil », « mateo_e4eb5cdc » →
 * « Mateo (poids modifiés) », « robert » → « Robert ». Les symboles boursiers restent tels quels.
 */
export function displayId(id: string, lang: "fr" | "en"): string {
  if (/^fictif(_[0-9a-f]+)?$/.test(id)) return lang === "en" ? "My profile" : "Mon profil";
  const m = /^(amira|mateo|robert)(_[0-9a-f]+)?$/.exec(id);
  if (!m) return id;
  const name = m[1].charAt(0).toUpperCase() + m[1].slice(1);
  return m[2] ? `${name} ${lang === "en" ? "(adjusted weights)" : "(poids modifiés)"}` : name;
}

export function useDisplayId(): (id: string) => string {
  const lang = useSettings((s) => s.lang);
  return useCallback((id: string) => displayId(id, lang), [lang]);
}
