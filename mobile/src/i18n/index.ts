/**
 * Langue de l'interface : `useT()` rend le dictionnaire courant (fr ou en) et fait
 * re-rendre le composant quand la langue change.
 */
import { useSettings } from "../store/settings";
import { en } from "./en";
import { fr, type Dict } from "./fr";
import { glossaire, glossaryEn } from "./glossaire";

export type { Dict };

export function useT(): Dict {
  const lang = useSettings((s) => s.lang);
  return lang === "en" ? en : fr;
}

export function useGlossary() {
  const lang = useSettings((s) => s.lang);
  return lang === "en" ? glossaryEn : glossaire;
}
