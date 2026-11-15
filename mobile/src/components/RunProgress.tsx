/**
 * Composant RunProgress — Étapes de l'analyse en cours, alimentées par l'état réel de l'exécution
 * (étapes de la machine d'états Step Functions). Barre de progression + liste verticale reliée.
 */
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { RunStatus } from "../types/contracts";
import { Icon } from "./Icon";
import { Card } from "./ui";

export function RunProgress({ steps }: { steps: RunStatus["steps"] }) {
  const t = useT();
  const done = steps.filter((s) => s.status === "ok").length;
  return (
    <Card style={{ gap: space.md }}>
      <View style={{ gap: 2 }}>
        <Text style={type.h3} accessibilityRole="header">{t.runProgress.title}</Text>
        <Text style={type.small} accessibilityLiveRegion="polite">
          {t.runProgress.stepOf(Math.min(done + 1, steps.length), steps.length)}
        </Text>
      </View>
      <View style={styles.bar}>
        <View style={[styles.fill, { width: `${(done / Math.max(1, steps.length)) * 100}%` }]} />
      </View>
      <View>
        {steps.map((s, i) => (
          <View key={s.id} style={styles.row} accessibilityLabel={`${t.steps[s.id]} : ${t.stepStatus[s.status]}`}>
            <View style={styles.rail}>
              <View style={[styles.node, s.status === "ok" && styles.nodeOk, s.status === "echec" && styles.nodeBad, s.status === "en_cours" && styles.nodeRun]}>
                {s.status === "en_cours" ? (
                  <ActivityIndicator size="small" color={colors.mint} />
                ) : s.status === "ok" ? (
                  <Icon name="check" size={14} color={colors.primaryText} strokeWidth={3} />
                ) : s.status === "echec" ? (
                  <Icon name="x" size={14} color={colors.bad} strokeWidth={3} />
                ) : null}
              </View>
              {i < steps.length - 1 ? <View style={[styles.line, s.status === "ok" && { backgroundColor: colors.primary }]} /> : null}
            </View>
            <Text style={[type.body, { flex: 1 }, s.status === "attente" && { color: colors.textMuted }]}>{t.steps[s.id]}</Text>
            <Text style={[type.caption, s.status === "en_cours" && { color: colors.mint }]}>{t.stepStatus[s.status]}</Text>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  bar: { height: 6, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, overflow: "hidden" },
  fill: { height: 6, borderRadius: radius.pill, backgroundColor: colors.primary },
  row: { flexDirection: "row", alignItems: "flex-start", gap: space.md, minHeight: 44 },
  rail: { width: 26, alignItems: "center", alignSelf: "stretch" },
  node: {
    width: 26, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center",
    borderWidth: 1.5, borderColor: colors.borderStrong, backgroundColor: colors.surface,
  },
  nodeOk: { backgroundColor: colors.primary, borderColor: colors.primary },
  nodeBad: { borderColor: colors.bad, backgroundColor: colors.badBg },
  nodeRun: { borderColor: colors.mint, backgroundColor: alpha(colors.mint, 0.08) },
  line: { flex: 1, width: 2, minHeight: 14, backgroundColor: colors.border, marginVertical: 2 },
});

export default RunProgress;
