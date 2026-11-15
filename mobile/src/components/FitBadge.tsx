/**
 * Composant FitBadge — Adéquation au profil (élevée / partielle / faible) et niveau de confiance.
 * Jauge à trois crans + libellé : jamais la couleur seule.
 * Adéquation : jade / ambre doré / corail. Confiance : pervenche (un axe distinct, pas « bon / mauvais »).
 */
import { useT } from "../i18n";
import { colors } from "../theme/tokens";
import type { Confidence, Fit } from "../types/contracts";
import { LevelMeter, Pill } from "./ui";

const FIT = {
  "élevée": { level: 3, fg: colors.good, bg: colors.goodBg },
  partielle: { level: 2, fg: colors.warn, bg: colors.warnBg },
  faible: { level: 1, fg: colors.bad, bg: colors.badBg },
} as const;

const CONF = { "élevée": 3, moyenne: 2, faible: 1 } as const;

export function FitBadge({ fit }: { fit: Fit }) {
  const t = useT();
  const s = FIT[fit];
  return <Pill leading={<LevelMeter level={s.level} color={s.fg} />} text={t.fit[fit]} fg={s.fg} bg={s.bg} />;
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const t = useT();
  return (
    <Pill
      leading={<LevelMeter level={CONF[confidence]} color={colors.info} shape="bar" />}
      text={t.confidence[confidence]}
      fg={colors.info}
      bg={colors.infoBg}
    />
  );
}

export default FitBadge;
