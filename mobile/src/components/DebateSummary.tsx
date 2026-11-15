/**
 * Composant DebateSummary — Trois positions (Bull / Réaliste / Bear) et désaccord conservé tel quel.
 * Mode Simple : position + premier argument. Mode Avancé : tous les arguments et questions ouvertes.
 */
import { StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { useSettings } from "../store/settings";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DebatePosition, Stance } from "../types/contracts";
import { ClaimLine } from "./EvidenceChip";
import { Icon, type IconName } from "./Icon";
import { Pill } from "./ui";

const STANCE: Record<Stance, { icon: string; fg: string; bg: string }> = {
  appui: { icon: "▲", fg: colors.good, bg: colors.goodBg },
  appui_reserve: { icon: "◆", fg: colors.warn, bg: colors.warnBg },
  opposition: { icon: "▼", fg: colors.bad, bg: colors.badBg },
};
const AGENT: Record<DebatePosition["agent"], IconName> = { bull: "sparkles", realist: "scale", bear: "trendingDown" };

export function DebateSummary({ debate, dissent, runId }: { debate: DebatePosition[]; dissent: boolean; runId?: string | null }) {
  const t = useT();
  const advanced = useSettings((s) => s.mode === "avance");
  return (
    <View style={{ gap: space.md }}>
      {dissent ? (
        <View style={styles.dissent}>
          <Icon name="scale" size={20} color={colors.warn} />
          <Text style={[type.body, { flex: 1 }]}>
            <Text style={{ fontWeight: "700", color: colors.warn }}>{t.debate.dissentStrong}</Text>
            {t.debate.dissentBody}
          </Text>
        </View>
      ) : null}
      {debate.map((d) => {
        const s = STANCE[d.stance];
        const args = advanced ? d.arguments : d.arguments.slice(0, 1);
        return (
          <View key={d.agent} style={[styles.card, { borderLeftColor: s.fg }]}>
            <View style={styles.head}>
              <Icon name={AGENT[d.agent] ?? "scale"} size={18} color={colors.mint} />
              <Text style={[type.h3, { flex: 1 }]}>{t.agent[d.agent]}</Text>
            </View>
            <View style={styles.badges}>
              <Pill icon={s.icon} text={t.stance[d.stance]} fg={s.fg} bg={s.bg} />
              {advanced ? <Pill text={t.confidence[d.confidence]} fg={colors.info} bg={colors.infoBg} /> : null}
            </View>
            {args.map((a) => (
              <ClaimLine key={a.text} claim={a} runId={runId} />
            ))}
            {advanced && d.open_questions.length > 0 ? (
              <Text style={type.small}>{t.debate.openQuestion(d.open_questions.join(" "))}</Text>
            ) : null}
          </View>
        );
      })}
      <Text style={type.caption}>{t.debate.caption}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    borderLeftWidth: 3, padding: space.md, gap: space.sm,
  },
  head: { flexDirection: "row", alignItems: "center", gap: space.sm },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  dissent: {
    flexDirection: "row", gap: space.md, alignItems: "flex-start",
    backgroundColor: colors.warnBg, borderRadius: radius.md, padding: space.md, borderWidth: 1, borderColor: alpha(colors.warn, 0.3),
  },
});

export default DebateSummary;
