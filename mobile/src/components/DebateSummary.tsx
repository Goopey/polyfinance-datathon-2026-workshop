/**
 * Composant DebateSummary — Trois positions et désaccord conservé tel quel.
 * Chaque agent a sa couleur : Bull vert vif, Réaliste jaune, Bear rouge vif (bordure, pastille, icône).
 * Une carte se déplie au toucher : arguments complets et questions ouvertes (dépliées d'office en mode Avancé).
 */
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { useTx } from "../i18n/data";
import { useSettings } from "../store/settings";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DebateAgent, DebatePosition, Stance } from "../types/contracts";
import { ClaimLine } from "./EvidenceChip";
import { Icon, type IconName } from "./Icon";
import { FadeIn, Pill, Tap } from "./ui";

export const AGENT_COLOR: Record<DebateAgent, string> = { bull: colors.bull, realist: colors.realist, bear: colors.bear };
const AGENT_ICON: Record<DebateAgent, IconName> = { bull: "trendingUp", realist: "scale", bear: "trendingDown" };
const STANCE_ICON: Record<Stance, string> = { appui: "▲", appui_reserve: "◆", opposition: "▼" };

export function DebateSummary({ debate, dissent, runId }: { debate: DebatePosition[]; dissent: boolean; runId?: string | null }) {
  const t = useT();
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
      {debate.map((d, i) => <AgentCard key={d.agent} d={d} index={i} runId={runId} />)}
    </View>
  );
}

function AgentCard({ d, index, runId }: { d: DebatePosition; index: number; runId?: string | null }) {
  const t = useT();
  const tx = useTx();
  const advanced = useSettings((s) => s.mode === "avance");
  const [open, setOpen] = useState(false);
  const color = AGENT_COLOR[d.agent];
  const expanded = open || advanced;
  const more = d.arguments.length > 1 || d.open_questions.length > 0;
  const args = expanded ? d.arguments : d.arguments.slice(0, 1);
  return (
    <FadeIn index={index}>
      <View style={[styles.card, { borderLeftColor: color, borderColor: alpha(color, 0.28) }]}>
        <Tap onPress={() => more && setOpen(!open)} disabled={!more || advanced} scaleTo={0.99}
          accessibilityRole="button" accessibilityState={{ expanded }} style={styles.head}>
          <View style={[styles.agentIcon, { backgroundColor: alpha(color, 0.16) }]}>
            <Icon name={AGENT_ICON[d.agent]} size={18} color={color} strokeWidth={2.4} />
          </View>
          <Text style={[type.h3, { flex: 1, color }]}>{t.agent[d.agent]}</Text>
          <Pill icon={STANCE_ICON[d.stance]} text={t.stance[d.stance]} fg={color} bg={alpha(color, 0.12)} />
        </Tap>
        {advanced ? <Pill text={t.confidence[d.confidence]} fg={colors.info} bg={colors.infoBg} /> : null}
        {args.map((a) => <ClaimLine key={a.text} claim={a} runId={runId} />)}
        {expanded && d.open_questions.length > 0 ? (
          <View style={styles.questions}>
            <Icon name="help" size={15} color={colors.textMuted} />
            <Text style={[type.small, { flex: 1 }]}>{d.open_questions.map(tx).join(" ")}</Text>
          </View>
        ) : null}
        {more && !advanced ? (
          <Tap onPress={() => setOpen(!open)} hitSlop={8} style={styles.more} accessibilityRole="button">
            <Text style={[styles.moreText, { color }]}>{open ? t.debate.less : t.debate.more(d.arguments.length - 1 + d.open_questions.length)}</Text>
            <Icon name={open ? "chevronUp" : "chevronDown"} size={14} color={color} />
          </Tap>
        ) : null}
      </View>
    </FadeIn>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1,
    borderLeftWidth: 4, padding: space.md, gap: space.sm,
  },
  head: { flexDirection: "row", alignItems: "center", gap: space.sm, flexWrap: "wrap" },
  agentIcon: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  questions: { flexDirection: "row", gap: space.sm, alignItems: "flex-start" },
  more: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", minHeight: 28 },
  moreText: { fontSize: 13.5, fontWeight: "700" },
  dissent: {
    flexDirection: "row", gap: space.md, alignItems: "flex-start",
    backgroundColor: colors.warnBg, borderRadius: radius.md, padding: space.md, borderWidth: 1, borderColor: alpha(colors.warn, 0.3),
  },
});

export default DebateSummary;
