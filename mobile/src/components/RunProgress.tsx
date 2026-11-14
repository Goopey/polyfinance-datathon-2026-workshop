/**
 * Composant RunProgress — Étapes de l'analyse en cours, alimentées par l'état réel de l'exécution
 * (étapes de la machine d'états Step Functions).
 */
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { fr } from "../i18n/fr";
import { colors, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { RunStatus } from "../types/contracts";
import { Card } from "./ui";

const ICON = { ok: "✓", echec: "✕", attente: "○" } as const;

export function RunProgress({ steps }: { steps: RunStatus["steps"] }) {
  const done = steps.filter((s) => s.status === "ok").length;
  return (
    <Card>
      <Text style={type.h3} accessibilityRole="header">Analyse en cours</Text>
      <Text style={type.small} accessibilityLiveRegion="polite">
        Étape {Math.min(done + 1, steps.length)} sur {steps.length}
      </Text>
      <View style={{ gap: space.sm, marginTop: space.sm }}>
        {steps.map((s) => (
          <View key={s.id} style={styles.row} accessibilityLabel={`${fr.steps[s.id]} : ${fr.stepStatus[s.status]}`}>
            <View style={styles.icon}>
              {s.status === "en_cours" ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={[styles.iconText, s.status === "ok" && { color: colors.good }, s.status === "echec" && { color: colors.bad }]}>
                  {ICON[s.status]}
                </Text>
              )}
            </View>
            <Text style={[type.body, s.status === "attente" && { color: colors.textMuted }]}>{fr.steps[s.id]}</Text>
            <Text style={[type.caption, { marginLeft: "auto" }]}>{fr.stepStatus[s.status]}</Text>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: space.md, minHeight: 32 },
  icon: { width: 24, alignItems: "center" },
  iconText: { fontSize: 18, fontWeight: "700", color: colors.textMuted },
});

export default RunProgress;
