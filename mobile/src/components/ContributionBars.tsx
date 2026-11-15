/**
 * Composant ContributionBars — Contribution de chaque critère au score d'adéquation (w_k · s_k).
 * La barre claire est le poids du critère (maximum possible), la barre pleine ce que l'actif en obtient.
 * Critère « sans objet » pour la classe d'actifs (ex. qualité d'un FNB) : pas de barre, la mention le dit, et
 * les poids affichés des autres critères sont rapportés aux critères applicables (comme le score).
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtNum } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import { CRITERIA, type Criterion, type CriterionMap } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";

export function ContributionBars({ contributions, weights: profileWeights, notApplicable = [] }: {
  contributions: CriterionMap; weights?: CriterionMap; notApplicable?: Criterion[];
}) {
  const t = useT();
  const na = new Set(notApplicable);
  const applicable = CRITERIA.filter((k) => !na.has(k));
  const total = CRITERIA.reduce((s, k) => s + contributions[k], 0);
  // Poids rapportés aux critères applicables : le score de l'actif l'est aussi (engine/scoring.py).
  const share = profileWeights ? applicable.reduce((s, k) => s + profileWeights[k], 0) || 1 : 1;
  const weights = profileWeights
    ? (Object.fromEntries(CRITERIA.map((k) => [k, na.has(k) ? 0 : profileWeights[k] / share])) as CriterionMap)
    : undefined;
  const maxW = weights ? Math.max(...applicable.map((k) => weights[k])) : Math.max(...applicable.map((k) => contributions[k]));
  const rows = [...applicable].sort((a, b) => contributions[b] - contributions[a]);
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
      {[...na].map((k) => (
        <View key={k} style={styles.labelRow} accessibilityLabel={`${t.criteria[k]} : ${t.contributions.notApplicable}`}>
          <Text style={[type.label, { color: colors.textMuted }]}>{t.criteria[k]}</Text>
          <Text style={type.small}>{t.contributions.notApplicable}</Text>
        </View>
      ))}
      {na.size > 0 ? (
        <Text style={type.caption}>{t.contributions.notApplicableNote([...na].map((k) => t.criteria[k]).join(", "))}</Text>
      ) : null}
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
