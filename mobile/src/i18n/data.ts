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
