/**
 * Composant PriceChart — Cours ajustés en CAD jusqu'à la date d'analyse (un point par semaine).
 * Données : GET /assets/{ticker}/prices. Décrit le passé ; ne prédit rien.
 * Interactif : glisser le doigt (ou la souris) sur la courbe affiche le cours et la date du point le plus proche.
 * Vectoriel (react-native-svg), dimensionné à la largeur réelle du conteneur.
 */
import { useState } from "react";
import { Platform, StyleSheet, Text, View, type GestureResponderEvent } from "react-native";
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from "react-native-svg";
import { fmtDate, fmtNum, fmtPct } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { PriceSeries } from "../types/contracts";
import { EvidenceChip } from "./EvidenceChip";

const HEIGHT = 170;
const PAD = { top: 12, bottom: 12 };

export function PriceChart({ series, runId }: { series: PriceSeries; runId?: string | null }) {
  const t = useT();
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const pts = series.points;
  if (pts.length < 2) return null; // une courbe a besoin d'au moins deux points
  const values = pts.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const up = series.change_pct >= 0;
  const tone = up ? colors.good : colors.bad;

  const x = (i: number) => (pts.length > 1 ? (i / (pts.length - 1)) * width : 0);
  const y = (v: number) => PAD.top + (1 - (v - min) / span) * (HEIGHT - PAD.top - PAD.bottom);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = `${line} L${width.toFixed(1)},${HEIGHT} L0,${HEIGHT} Z`;
  const lastIndex = pts.length - 1;
  const focus = hover ?? lastIndex;
  const fp = pts[focus];
  const fromStart = (fp.value / pts[0].value - 1) * 100;

  const pick = (lx: number) => {
    if (width <= 0 || pts.length < 2) return;
    setHover(Math.max(0, Math.min(lastIndex, Math.round((lx / width) * lastIndex))));
  };
  const onTouch = (e: GestureResponderEvent) => pick(e.nativeEvent.locationX);
  // Survol à la souris (web) : react-native-web transmet les évènements de pointeur.
  const webHover = Platform.OS === "web"
    ? {
      onPointerMove: (e: { nativeEvent: { offsetX: number } }) => pick(e.nativeEvent.offsetX),
      onPointerLeave: () => setHover(null),
    }
    : {};

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <View style={{ gap: 2, flex: 1, minWidth: 140 }}>
          <Text style={styles.price}>{`${fmtNum(fp.value, 2)} ${series.currency}`}</Text>
          <Text style={[type.small, { color: fromStart >= 0 ? colors.good : colors.bad, fontWeight: "700" }]}>
            {`${fromStart >= 0 ? "+" : "−"}${fmtPct(Math.abs(fromStart))} `}
            <Text style={{ color: colors.textMuted, fontWeight: "500" }}>{t.priceChart.since(fmtDate(series.start))}</Text>
          </Text>
        </View>
        <View style={styles.datePill}>
          <Text style={styles.dateText}>{hover === null ? t.priceChart.asOf(fmtDate(fp.day)) : fmtDate(fp.day)}</Text>
        </View>
      </View>
      <View
        style={{ height: HEIGHT }}
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderGrant={onTouch}
        onResponderMove={onTouch}
        onResponderRelease={() => setHover(null)}
        onResponderTerminate={() => setHover(null)}
        accessible
        accessibilityLabel={t.priceChart.a11y(series.ticker, fmtPct(series.change_pct), fmtDate(series.start), fmtDate(series.end))}
        {...(webHover as object)}
      >
        {width > 0 && pts.length > 1 ? (
          <Svg width={width} height={HEIGHT} pointerEvents="none">
            <Defs>
              <LinearGradient id={`price-${series.ticker}`} x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor={tone} stopOpacity="0.28" />
                <Stop offset="1" stopColor={tone} stopOpacity="0" />
              </LinearGradient>
            </Defs>
            <Line x1="0" x2={width} y1={y(values[0])} y2={y(values[0])} stroke={alpha(colors.mint, 0.25)}
              strokeWidth={1} strokeDasharray="4 5" />
            <Path d={area} fill={`url(#price-${series.ticker})`} />
            <Path d={line} stroke={tone} strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            {hover !== null ? (
              <Line x1={x(focus)} x2={x(focus)} y1={0} y2={HEIGHT} stroke={alpha(colors.mint, 0.5)} strokeWidth={1} />
            ) : null}
            <Circle cx={x(focus)} cy={y(fp.value)} r={hover !== null ? 6 : 4.5} fill={tone} stroke={colors.bg} strokeWidth={2} />
          </Svg>
        ) : null}
      </View>
      <View style={styles.scale}>
        <Text style={type.caption}>{t.priceChart.low(fmtNum(min, 2), series.currency)}</Text>
        <Text style={type.caption}>{t.priceChart.high(fmtNum(max, 2), series.currency)}</Text>
      </View>
      <View style={styles.meta}>
        <Text style={[type.caption, { flexShrink: 1 }]}>{t.priceChart.hint}</Text>
        {series.evidence_id ? <EvidenceChip id={series.evidence_id} runId={runId} /> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.sm },
  head: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: space.sm },
  price: { fontSize: 24, fontWeight: "800", color: colors.text, letterSpacing: -0.4 },
  datePill: { backgroundColor: colors.surfaceRaised, borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4 },
  dateText: { fontSize: 12.5, fontWeight: "700", color: colors.mint },
  scale: { flexDirection: "row", justifyContent: "space-between" },
  meta: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: space.sm },
});

export default PriceChart;
