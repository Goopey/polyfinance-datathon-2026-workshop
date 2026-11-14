/**
 * Composant ClaimTag — Étiquette Hypothèse / Scénario fictif, visible sans action (docs/05_EXPLICABILITE.md §2).
 * Un fait n'a pas d'étiquette (sa pastille de source suffit), sauf si `showFact`.
 */
import { fr } from "../i18n/fr";
import { colors } from "../theme/tokens";
import type { ClaimKind } from "../types/contracts";
import { Pill } from "./ui";

export function ClaimTag({ kind, showFact = false }: { kind: ClaimKind; showFact?: boolean }) {
  if (kind === "HYPOTHESE") return <Pill icon="◇" text={fr.claimKind.HYPOTHESE} fg={colors.hypothesis} bg={colors.hypothesisBg} />;
  if (kind === "SCENARIO") return <Pill icon="◌" text={fr.claimKind.SCENARIO} fg={colors.scenario} bg={colors.scenarioBg} />;
  if (showFact) return <Pill icon="■" text={fr.claimKind.FAIT} fg={colors.text} bg={colors.neutralBg} />;
  return null;
}

export default ClaimTag;
