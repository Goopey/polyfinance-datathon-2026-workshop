/**
 * Composant ContributionBars — Contribution de chaque critère au score d'adéquation (w_k · s_k), sur 100 points.
 * Toutes les barres partagent la même échelle de 0 à 100 points : la barre claire est le poids du critère
 * (maximum possible), la barre pleine ce que l'actif en obtient. Les longueurs sont donc comparables entre elles
 * et avec le score total (anneau).
 * Critère « sans objet » pour la classe d'actifs (ex. qualité d'un FNB) : pas de barre, la mention le dit, et
 * les poids affichés des autres critères sont rapportés aux critères applicables (comme le score).
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtNum } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { CRITERIA, type Criterion, type CriterionMap } from "../types/contracts";
import { ScoreRing } from "./ScoreRing";

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
  const rows = [...applicable].sort((a, b) => contributions[b] - contributions[a]);
  const pct = (x: number) => `${Math.max(0, Math.min(100, x * 100))}%` as const;
  return (
    <View style={{ gap: space.md }}>
      <View style={styles.scoreRow}>
        <ScoreRing score={total * 100} size={76} label={t.contributions.scoreValue(fmtNum(total * 100, 0))} />
        <Text style={[type.small, { flex: 1 }]}>{t.contributions.score}</Text>
      </View>
      {rows.map((k) => {
        const c = contributions[k];
        const w = weights?.[k];
        const cs = fmtNum(c * 100, 0);
        const ws = w !== undefined ? fmtNum(w * 100, 0) : undefined;
        return (
          <View key={k} style={{ gap: 6 }} accessible accessibilityLabel={t.contributions.a11y(t.criteria[k], cs, ws)}>
            <View style={styles.labelRow}>
              <Text style={type.label}>{t.criteria[k]}</Text>
              <Text style={type.small}>{t.contributions.pts(cs, ws)}</Text>
            </View>
            <View style={styles.track}>
              {w !== undefined ? <View style={[styles.weight, { width: pct(w) }]} /> : null}
              <View style={[styles.value, { width: pct(c) }]} />
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
      <View style={styles.legend}>
        <View style={[styles.swatch, { backgroundColor: alpha(colors.primary, 0.28) }]} />
        <Text style={type.caption}>{t.contributions.legendWeight}</Text>
        <View style={[styles.swatch, { backgroundColor: colors.primary }]} />
        <Text style={type.caption}>{t.contributions.legendValue}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scoreRow: { flexDirection: "row", alignItems: "center", gap: space.md },
  labelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: space.sm },
  track: { height: 10, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, overflow: "hidden" },
  weight: { position: "absolute", top: 0, bottom: 0, left: 0, borderRadius: radius.pill, backgroundColor: alpha(colors.primary, 0.28) },
  value: { position: "absolute", top: 0, bottom: 0, left: 0, borderRadius: radius.pill, backgroundColor: colors.primary },
  legend: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  swatch: { width: 14, height: 8, borderRadius: 4, marginLeft: 4 },
});

export default ContributionBars;
