/**
 * Composant RiskMeter — Indicateur observé, dessiné à l'échelle réelle (proportionnel à 100 %).
 *
 * - Volatilité, perte maximale : barre de 0 à 100 % ; la longueur de la barre est la valeur elle-même
 *   (27,8 % de volatilité = 27,8 % de la piste). Le seuil indicatif du profil est un trait à sa vraie place.
 * - Rendements (annualisé, 2022, pire période de 3 ans) : échelle de −100 % à +100 % centrée sur 0 ;
 *   au-delà de ±100 %, la barre est pleine et une flèche le signale.
 * Couleur doublée d'un libellé (« au-delà / sous votre seuil »), jamais seule.
 */
import { useEffect, useRef } from "react";
import { Animated, Easing, Platform, StyleSheet, Text, View } from "react-native";
import { fmtPct } from "../format";
import { useT } from "../i18n";
import { useTx } from "../i18n/data";
import { useSettings } from "../store/settings";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { AssetMetric } from "../types/contracts";
import { EvidenceChip } from "./EvidenceChip";
import { GlossaryTerm } from "./GlossaryTerm";
import { Icon } from "./Icon";
import { settle, webGrow } from "./ui";

const GLOSSARY: Record<string, string> = {
  volatilite: "volatilite", perte_max: "perte_max", pire_periode: "pire_periode", rendement_annualise: "rendement_annualise",
};
/** Indicateurs signés : échelle centrée sur 0. */
const SIGNED = new Set(["rendement_annualise", "rendement_2022", "pire_periode"]);
/** Pour ces indicateurs, une valeur plus basse dépasse le seuil (pertes, négatives). */
const LOWER_IS_RISKIER = new Set(["perte_max", "pire_periode"]);

export function RiskMeter({ m, runId }: { m: AssetMetric; runId?: string | null }) {
  const t = useT();
  const tx = useTx();
  const advanced = useSettings((s) => s.mode === "avance");
  const signed = SIGNED.has(m.metric);
  const label = t.metrics[m.metric as keyof typeof t.metrics] ?? tx(m.label);
  const limit = m.profile_limit;
  const over = limit !== null && (LOWER_IS_RISKIER.has(m.metric) ? m.value < limit : m.value > limit);
  const overflow = Math.abs(m.value) > 100;
  const mag = Math.min(100, Math.abs(m.value)); // part de la piste, en %

  const tone = signed
    ? (m.value >= 0 ? colors.good : colors.bad)
    : limit !== null ? (over ? colors.bad : colors.good) : m.metric === "perte_max" ? colors.warn : colors.info;

  // Barre qui se remplit à l'affichage. Sa longueur finale est toujours exacte : sur le web, largeur
  // statique et images clés CSS ; sur téléphone, `settle` garantit la valeur finale.
  const target = `${signed ? mag / 2 : mag}%`;
  const grow = useRef(new Animated.Value(Platform.OS === "web" ? 1 : 0)).current;
  useEffect(() => {
    if (Platform.OS === "web") return;
    settle(Animated.timing(grow, { toValue: 1, duration: 650, easing: Easing.out(Easing.cubic), useNativeDriver: false }),
      grow, 1);
  }, [grow]);
  const width = Platform.OS === "web" ? target : grow.interpolate({ inputRange: [0, 1], outputRange: ["0%", target] });

  return (
    <View style={styles.wrap} accessible accessibilityLabel={t.riskMeter.a11y(label, fmtPct(m.value), tx(m.window))}>
      <View style={styles.head}>
        <View style={{ flex: 1, gap: 2 }}>
          <GlossaryTerm id={GLOSSARY[m.metric] ?? m.metric} label={label} />
          {advanced ? <Text style={type.caption}>{tx(m.window)}</Text> : null}
        </View>
        <Text style={[styles.value, { color: tone }]}>{fmtPct(m.value)}</Text>
      </View>

      <View style={styles.track}>
        {signed ? <View style={styles.zero} /> : null}
        <Animated.View
          style={[
            styles.fill,
            { width, backgroundColor: tone },
            signed ? (m.value >= 0 ? { left: "50%" } : { right: "50%" }) : { left: 0 },
            Platform.OS === "web" ? webGrow(target) : null,
          ]}
        />
        {limit !== null ? (
          <View style={[styles.limit, { left: `${signed ? 50 + Math.max(-100, Math.min(100, limit)) / 2 : Math.min(100, Math.abs(limit))}%` }]} />
        ) : null}
        {overflow ? (
          <View style={[styles.overflow, m.value >= 0 ? { right: 2 } : { left: 2 }]}>
            <Icon name={m.value >= 0 ? "chevronRight" : "chevronLeft"} size={12} color={colors.primaryText} strokeWidth={3} />
          </View>
        ) : null}
      </View>
      <View style={styles.scale}>
        <Text style={type.caption}>{signed ? `−100${t.riskMeter.pctSpace}%` : `0${t.riskMeter.pctSpace}%`}</Text>
        {signed ? <Text style={type.caption}>0</Text> : null}
        <Text style={type.caption}>{signed ? "+" : ""}100{t.riskMeter.pctSpace}%</Text>
      </View>

      <View style={styles.meta}>
        {limit !== null ? (
          <View style={styles.verdict}>
            <Icon name={over ? "x" : "check"} size={15} color={over ? colors.bad : colors.good} strokeWidth={2.8} />
            <Text style={[type.small, { color: over ? colors.bad : colors.good, fontWeight: "600", flexShrink: 1 }]}>
              {over ? t.riskMeter.beyond(fmtPct(limit, 0)) : t.riskMeter.within(fmtPct(limit, 0))}
            </Text>
          </View>
        ) : <View style={{ flex: 1 }} />}
        <EvidenceChip id={m.evidence_id} runId={runId} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.xs + 2, paddingVertical: space.md, borderBottomWidth: 1, borderBottomColor: alpha(colors.mint, 0.06) },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: space.md },
  value: { fontSize: 20, fontWeight: "800", letterSpacing: -0.3 },
  track: { height: 12, borderRadius: radius.pill, marginTop: space.xs, backgroundColor: colors.surfaceRaised, overflow: "visible" },
  fill: { position: "absolute", top: 0, bottom: 0, borderRadius: radius.pill },
  zero: { position: "absolute", left: "50%", top: -3, bottom: -3, width: 2, marginLeft: -1, backgroundColor: alpha(colors.mint, 0.45) },
  limit: { position: "absolute", top: -6, width: 3, height: 24, marginLeft: -1.5, borderRadius: 2, backgroundColor: colors.text },
  overflow: { position: "absolute", top: 0, bottom: 0, justifyContent: "center" },
  scale: { flexDirection: "row", justifyContent: "space-between" },
  meta: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: space.sm },
  verdict: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1, minWidth: 180 },
});

export default RiskMeter;
