/**
 * Composant FitBadge — Adéquation au profil (élevée / partielle / faible). Icône + libellé : jamais la couleur seule.
 */
import { fr } from "../i18n/fr";
import { colors } from "../theme/tokens";
import type { Confidence, Fit } from "../types/contracts";
import { Pill } from "./ui";

const FIT = {
  "élevée": { icon: "●●●", fg: colors.good, bg: colors.goodBg },
  partielle: { icon: "●●○", fg: colors.warn, bg: colors.warnBg },
  faible: { icon: "●○○", fg: colors.bad, bg: colors.badBg },
} as const;

export function FitBadge({ fit }: { fit: Fit }) {
  const s = FIT[fit];
  return <Pill icon={s.icon} text={fr.fit[fit]} fg={s.fg} bg={s.bg} />;
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const icon = confidence === "élevée" ? "▮▮▮" : confidence === "moyenne" ? "▮▮▯" : "▮▯▯";
  return <Pill icon={icon} text={fr.confidence[confidence]} fg={colors.text} bg={colors.neutralBg} />;
}

export default FitBadge;
