/**
 * Composant RiskMeter — Indicateur de risque situé dans l'univers et comparé au seuil indicatif du profil.
 * L'échelle est orientée pour que « plus risqué » soit toujours à droite (dégradé jade → ambre → corail).
 */
import { StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";
import { fmtPct } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { AssetMetric } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { EvidenceChip } from "./EvidenceChip";
import { GlossaryTerm } from "./GlossaryTerm";
import { Icon } from "./Icon";

const GLOSSARY: Record<string, string> = {
  volatilite: "volatilite", perte_max: "perte_max", pire_periode: "pire_periode", rendement_annualise: "rendement_annualise",
};
/** Indicateurs de rendement : situés dans l'univers sans lecture « plus risqué ». */
const RETURNS = new Set(["rendement_annualise", "rendement_2022"]);
/** Pour ces indicateurs, une valeur plus basse est plus risquée. */
const LOWER_IS_RISKIER = new Set(["perte_max", "pire_periode"]);

export function RiskMeter({ m, runId }: { m: AssetMetric; runId?: string | null }) {
  const t = useT();
  const isRisk = !RETURNS.has(m.metric);
  const invert = LOWER_IS_RISKIER.has(m.metric);
  const span = m.universe_max - m.universe_min || 1;
  const pos = (v: number) => {
    const p = (v - m.universe_min) / span;
    return Math.max(0, Math.min(1, invert ? 1 - p : p));
  };
  const over = m.profile_limit !== null && (invert ? m.value < m.profile_limit : m.value > m.profile_limit);
  const gid = `risk-${m.metric}`;
  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <GlossaryTerm id={GLOSSARY[m.metric] ?? m.metric} label={m.label} />
        <Text style={type.h3}>{fmtPct(m.value)}</Text>
      </View>
      <View style={styles.track} accessibilityLabel={t.riskMeter.a11y(m.label, fmtPct(m.value), m.window)}>
        <Svg width="100%" height="100%" style={StyleSheet.absoluteFill}>
          <Defs>
            <LinearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
              {(isRisk
                ? [
                  { o: "0", c: colors.good, a: "0.55" },
                  { o: "0.55", c: colors.warn, a: "0.55" },
                  { o: "1", c: colors.bad, a: "0.6" },
                ]
                : [
                  { o: "0", c: colors.surfaceRaised, a: "1" },
                  { o: "1", c: colors.primary, a: "0.6" },
                ]
              ).map((s) => <Stop key={s.o} offset={s.o} stopColor={s.c} stopOpacity={s.a} />)}
            </LinearGradient>
          </Defs>
          <Rect x="0" y="0" width="100%" height="100%" rx="6" fill={`url(#${gid})`} />
        </Svg>
        <View style={[styles.marker, { left: `${pos(m.value) * 100}%` }]} />
        {m.profile_limit !== null ? <View style={[styles.limit, { left: `${pos(m.profile_limit) * 100}%` }]} /> : null}
      </View>
      <View style={styles.scale}>
        <Text style={type.caption}>← {isRisk ? t.riskMeter.lessRisky : t.riskMeter.lower} {t.riskMeter.universe}</Text>
        <Text style={type.caption}>{isRisk ? t.riskMeter.moreRisky : t.riskMeter.higher} →</Text>
      </View>
      {m.profile_limit !== null ? (
        <View style={styles.meta}>
          <Icon name={over ? "x" : "check"} size={16} color={over ? colors.bad : colors.good} strokeWidth={2.6} />
          <Text style={[type.small, { flexShrink: 1 }, over ? { color: colors.bad, fontWeight: "600" } : { color: colors.good }]}>
            {over ? t.riskMeter.beyond(fmtPct(m.profile_limit, 0)) : t.riskMeter.within(fmtPct(m.profile_limit, 0))}
          </Text>
          <ClaimTag kind="HYPOTHESE" />
        </View>
      ) : null}
      <View style={styles.meta}>
        <Text style={type.caption}>{t.riskMeter.observed(m.window)}</Text>
        <EvidenceChip id={m.evidence_id} runId={runId} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.xs + 2, paddingVertical: space.md, borderBottomWidth: 1, borderBottomColor: alpha(colors.mint, 0.06) },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  track: { height: 12, borderRadius: radius.pill, marginTop: space.xs, justifyContent: "center", overflow: "visible" },
  marker: {
    position: "absolute", width: 22, height: 22, borderRadius: 11, marginLeft: -11,
    backgroundColor: colors.mint, borderWidth: 4, borderColor: colors.bg,
    shadowColor: colors.mint, shadowOpacity: 0.6, shadowRadius: 8, shadowOffset: { width: 0, height: 0 },
  },
  limit: { position: "absolute", width: 3, height: 28, marginLeft: -1.5, borderRadius: 2, backgroundColor: colors.text },
  scale: { flexDirection: "row", justifyContent: "space-between" },
  meta: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: space.sm },
});

export default RiskMeter;
