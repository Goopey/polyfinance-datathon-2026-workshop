/**
 * Composant RiskMeter — Indicateur de risque situé dans l'univers et comparé au seuil indicatif du profil.
 * L'échelle est orientée pour que « plus risqué » soit toujours à droite.
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtPct } from "../format";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { AssetMetric } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { EvidenceChip } from "./EvidenceChip";
import { GlossaryTerm } from "./GlossaryTerm";

const GLOSSARY: Record<string, string> = {
  volatilite: "volatilite", perte_max: "perte_max", pire_periode: "pire_periode", rendement_annualise: "rendement_annualise",
};
/** Pour ces indicateurs, une valeur plus basse est plus risquée. */
const LOWER_IS_RISKIER = new Set(["perte_max", "pire_periode"]);

export function RiskMeter({ m, runId }: { m: AssetMetric; runId?: string | null }) {
  const isRisk = m.metric !== "rendement_annualise";
  const invert = LOWER_IS_RISKIER.has(m.metric);
  const span = m.universe_max - m.universe_min || 1;
  const pos = (v: number) => {
    const p = (v - m.universe_min) / span;
    return Math.max(0, Math.min(1, invert ? 1 - p : p));
  };
  const over = m.profile_limit !== null && (invert ? m.value < m.profile_limit : m.value > m.profile_limit);
  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <GlossaryTerm id={GLOSSARY[m.metric] ?? m.metric} label={m.label} />
        <Text style={type.h3}>{fmtPct(m.value)}</Text>
      </View>
      <View style={styles.track} accessibilityLabel={`${m.label} : ${fmtPct(m.value)}, fenêtre ${m.window}`}>
        <View style={[styles.marker, { left: `${pos(m.value) * 100}%` }]} />
        {m.profile_limit !== null ? <View style={[styles.limit, { left: `${pos(m.profile_limit) * 100}%` }]} /> : null}
      </View>
      <View style={styles.scale}>
        <Text style={type.caption}>{isRisk ? "← moins risqué" : "← plus bas"} (univers)</Text>
        <Text style={type.caption}>{isRisk ? "plus risqué →" : "plus haut →"}</Text>
      </View>
      {m.profile_limit !== null ? (
        <View style={styles.meta}>
          <Text style={[type.small, over && { color: colors.bad, fontWeight: "600" }]}>
            {over ? "✕ Au-delà" : "✓ En deçà"} du seuil indicatif du profil ({fmtPct(m.profile_limit, 0)}, trait vertical)
          </Text>
          <ClaimTag kind="HYPOTHESE" />
        </View>
      ) : null}
      <View style={styles.meta}>
        <Text style={type.caption}>Observé sur {m.window} ; décrit le passé, ne prédit rien.</Text>
        <EvidenceChip id={m.evidence_id} runId={runId} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.xs, paddingVertical: space.sm },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  track: { height: 12, borderRadius: radius.pill, backgroundColor: colors.surfaceMuted, marginTop: space.xs, justifyContent: "center" },
  marker: {
    position: "absolute", width: 20, height: 20, borderRadius: 10, marginLeft: -10,
    backgroundColor: colors.primary, borderWidth: 3, borderColor: colors.surface,
  },
  limit: { position: "absolute", width: 3, height: 26, marginLeft: -1.5, backgroundColor: colors.text },
  scale: { flexDirection: "row", justifyContent: "space-between" },
  meta: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: space.sm },
});

export default RiskMeter;
