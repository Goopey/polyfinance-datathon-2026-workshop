/**
 * Composant DebateSummary — Trois positions (Bull / Réaliste / Bear) et désaccord conservé tel quel.
 * Mode Simple : position + premier argument. Mode Avancé : tous les arguments et questions ouvertes.
 */
import { StyleSheet, Text, View } from "react-native";
import { fr } from "../i18n/fr";
import { useSettings } from "../store/settings";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DebatePosition, Stance } from "../types/contracts";
import { ClaimLine } from "./EvidenceChip";
import { Pill } from "./ui";

const STANCE: Record<Stance, { icon: string; fg: string; bg: string }> = {
  appui: { icon: "▲", fg: colors.good, bg: colors.goodBg },
  appui_reserve: { icon: "◆", fg: colors.warn, bg: colors.warnBg },
  opposition: { icon: "▼", fg: colors.bad, bg: colors.badBg },
};

export function DebateSummary({ debate, dissent, runId }: { debate: DebatePosition[]; dissent: boolean; runId?: string | null }) {
  const advanced = useSettings((s) => s.mode === "avance");
  return (
    <View style={{ gap: space.md }}>
      {dissent ? (
        <View style={styles.dissent}>
          <Text style={type.body}>
            ⚖ <Text style={{ fontWeight: "700" }}>Désaccord conservé.</Text> Les trois agents ont reçu les mêmes preuves et
            n'arrivent pas à la même position : la confiance en tient compte.
          </Text>
        </View>
      ) : null}
      {debate.map((d) => {
        const s = STANCE[d.stance];
        const args = advanced ? d.arguments : d.arguments.slice(0, 1);
        return (
          <View key={d.agent} style={styles.card}>
            <Text style={type.h3}>{fr.agent[d.agent]}</Text>
            <View style={styles.badges}>
              <Pill icon={s.icon} text={fr.stance[d.stance]} fg={s.fg} bg={s.bg} />
              {advanced ? <Pill text={fr.confidence[d.confidence]} fg={colors.text} bg={colors.neutralBg} /> : null}
            </View>
            {args.map((a) => (
              <ClaimLine key={a.text} claim={a} runId={runId} />
            ))}
            {advanced && d.open_questions.length > 0 ? (
              <Text style={type.small}>Question ouverte : {d.open_questions.join(" ")}</Text>
            ) : null}
          </View>
        );
      })}
      <Text style={type.caption}>
        Les agents argumentent à partir des preuves ; ils ne produisent aucun chiffre et ne décident pas. Le classement vient du moteur de décision.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: space.md, gap: space.sm },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  dissent: { backgroundColor: colors.warnBg, borderRadius: radius.md, padding: space.md },
});

export default DebateSummary;
