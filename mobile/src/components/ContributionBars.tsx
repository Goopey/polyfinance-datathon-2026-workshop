/**
 * Composant ContributionBars — Contribution de chaque critère au score d'adéquation (w_k · s_k).
 * La barre claire est le poids du critère (maximum possible), la barre pleine ce que l'actif en obtient.
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtNum } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import { CRITERIA, type CriterionMap } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";

export function ContributionBars({ contributions, weights }: { contributions: CriterionMap; weights?: CriterionMap }) {
  const t = useT();
  const total = CRITERIA.reduce((s, k) => s + contributions[k], 0);
  const maxW = weights ? Math.max(...CRITERIA.map((k) => weights[k])) : Math.max(...CRITERIA.map((k) => contributions[k]));
  const rows = [...CRITERIA].sort((a, b) => contributions[b] - contributions[a]);
  return (
    <View style={{ gap: space.md }}>
      <View style={styles.scoreRow}>
        <Text style={styles.score}>{fmtNum(total * 100, 0)}</Text>
        <Text style={[type.small, { flex: 1 }]}>
          {t.contributions.score}
          <Text style={{ fontWeight: "700", color: colors.text }}>{t.contributions.scoreValue(fmtNum(total * 100, 0))}</Text>
        </Text>
      </View>
      {rows.map((k) => {
        const c = contributions[k];
        const w = weights?.[k];
        const cs = fmtNum(c * 100, 0);
        const ws = w !== undefined ? fmtNum(w * 100, 0) : undefined;
        return (
          <View key={k} style={{ gap: 6 }} accessibilityLabel={t.contributions.a11y(t.criteria[k], cs, ws)}>
            <View style={styles.labelRow}>
              <Text style={type.label}>{t.criteria[k]}</Text>
              <Text style={type.small}>{t.contributions.pts(cs, ws)}</Text>
            </View>
            <View style={styles.track}>
              {w !== undefined ? <View style={[styles.weight, { width: `${(w / maxW) * 100}%` }]} /> : null}
              <View style={[styles.value, { width: `${(c / maxW) * 100}%` }]} />
            </View>
          </View>
        );
      })}
      <View style={styles.labelRow}>
        <Text style={[type.caption, { flex: 1 }]}>{t.contributions.caption}</Text>
        <ClaimTag kind="HYPOTHESE" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scoreRow: { flexDirection: "row", alignItems: "center", gap: space.md },
  score: { fontFamily, fontSize: 40, fontWeight: "800", color: colors.mint, letterSpacing: -1 },
  labelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: space.sm },
  track: { height: 12, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, overflow: "hidden" },
  weight: { position: "absolute", top: 0, bottom: 0, left: 0, borderRadius: radius.pill, backgroundColor: alpha(colors.primary, 0.28) },
  value: { position: "absolute", top: 0, bottom: 0, left: 0, borderRadius: radius.pill, backgroundColor: colors.primary },
});

export default ContributionBars;
