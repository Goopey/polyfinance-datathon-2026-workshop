/**
 * Composant ClaimTag — Étiquette Hypothèse / Scénario, visible sans action (docs/05_EXPLICABILITE.md §2).
 * Un fait n'a pas d'étiquette (sa pastille de source suffit), sauf si `showFact`.
 */
import { useT } from "../i18n";
import { colors } from "../theme/tokens";
import type { ClaimKind } from "../types/contracts";
import { Pill } from "./ui";

export function ClaimTag({ kind, showFact = false }: { kind: ClaimKind; showFact?: boolean }) {
  const t = useT();
  if (kind === "HYPOTHESE") return <Pill icon="◇" text={t.claimKind.HYPOTHESE} fg={colors.hypothesis} bg={colors.hypothesisBg} />;
  if (kind === "SCENARIO") return <Pill icon="◌" text={t.claimKind.SCENARIO} fg={colors.scenario} bg={colors.scenarioBg} />;
  if (showFact) return <Pill icon="check" text={t.claimKind.FAIT} fg={colors.mint} bg={colors.neutralBg} />;
  return null;
}

export default ClaimTag;
