/**
 * Composant ContributionBars — Contribution de chaque critère au score d'adéquation (w_k · s_k).
 * La barre claire est le poids du critère (maximum possible), la barre foncée ce que l'actif en obtient.
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtNum } from "../format";
import { fr } from "../i18n/fr";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { CRITERIA, type CriterionMap } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";

export function ContributionBars({ contributions, weights }: { contributions: CriterionMap; weights?: CriterionMap }) {
  const total = CRITERIA.reduce((s, k) => s + contributions[k], 0);
  const maxW = weights ? Math.max(...CRITERIA.map((k) => weights[k])) : Math.max(...CRITERIA.map((k) => contributions[k]));
  const rows = [...CRITERIA].sort((a, b) => contributions[b] - contributions[a]);
  return (
    <View style={{ gap: space.md }}>
      <Text style={type.body}>
        Score d'adéquation : <Text style={{ fontWeight: "700" }}>{fmtNum(total * 100, 0)} points sur 100</Text>
      </Text>
      {rows.map((k) => {
        const c = contributions[k];
        const w = weights?.[k];
        return (
          <View key={k} style={{ gap: 4 }} accessibilityLabel={`${fr.criteria[k]} : ${fmtNum(c * 100, 0)} points${w !== undefined ? ` sur ${fmtNum(w * 100, 0)} possibles` : ""}`}>
            <View style={styles.labelRow}>
              <Text style={type.label}>{fr.criteria[k]}</Text>
              <Text style={type.small}>
                {fmtNum(c * 100, 0)} pts{w !== undefined ? ` / ${fmtNum(w * 100, 0)}` : ""}
              </Text>
            </View>
            <View style={styles.track}>
              {w !== undefined ? <View style={[styles.weight, { width: `${(w / maxW) * 100}%` }]} /> : null}
              <View style={[styles.value, { width: `${(c / maxW) * 100}%` }]} />
            </View>
          </View>
        );
      })}
      <View style={styles.labelRow}>
        <Text style={[type.caption, { flex: 1 }]}>Poids du profil et critères : choix de l'équipe, à calibrer. Le débat ne modifie pas le score.</Text>
        <ClaimTag kind="HYPOTHESE" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  labelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: space.sm },
  track: { height: 14, borderRadius: radius.sm, backgroundColor: colors.surfaceMuted, overflow: "hidden" },
  weight: { position: "absolute", top: 0, bottom: 0, left: 0, backgroundColor: "#C9D6F7" },
  value: { position: "absolute", top: 0, bottom: 0, left: 0, backgroundColor: colors.primary },
});

export default ContributionBars;
