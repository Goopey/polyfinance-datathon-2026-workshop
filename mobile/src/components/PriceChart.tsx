/**
 * Composant PriceChart — Cours ajustés en CAD jusqu'à la date d'analyse (un point par semaine).
 * Données : GET /assets/{ticker}/prices. Décrit le passé ; ne prédit rien.
 * Vectoriel (react-native-svg), dimensionné à la largeur réelle du conteneur.
 */
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from "react-native-svg";
import { fmtDate, fmtNum, fmtPct } from "../format";
import { useT } from "../i18n";
import { alpha, colors, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { PriceSeries } from "../types/contracts";
import { EvidenceChip } from "./EvidenceChip";

const HEIGHT = 170;
const PAD = { top: 12, bottom: 12 };

export function PriceChart({ series, runId }: { series: PriceSeries; runId?: string | null }) {
  const t = useT();
  const [width, setWidth] = useState(0);
  const values = series.points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const up = series.change_pct >= 0;
  const tone = up ? colors.good : colors.bad;

  const x = (i: number) => (series.points.length > 1 ? (i / (series.points.length - 1)) * width : 0);
  const y = (v: number) => PAD.top + (1 - (v - min) / span) * (HEIGHT - PAD.top - PAD.bottom);
  const line = series.points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = `${line} L${width.toFixed(1)},${HEIGHT} L0,${HEIGHT} Z`;
  const last = series.points[series.points.length - 1];

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={[type.h2, { color: tone }]}>{`${up ? "+" : "−"}${fmtPct(Math.abs(series.change_pct))}`}</Text>
        <Text style={[type.caption, { flexShrink: 1, textAlign: "right" }]}>
          {t.priceChart.period(fmtDate(series.start), fmtDate(series.end))}
        </Text>
      </View>
      <View
        style={{ height: HEIGHT }}
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        accessible
        accessibilityLabel={t.priceChart.a11y(series.ticker, fmtPct(series.change_pct), fmtDate(series.start), fmtDate(series.end))}
      >
        {width > 0 && series.points.length > 1 ? (
          <Svg width={width} height={HEIGHT}>
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
            <Circle cx={x(series.points.length - 1)} cy={y(last.value)} r={4.5} fill={tone} stroke={colors.bg} strokeWidth={2} />
          </Svg>
        ) : null}
      </View>
      <View style={styles.scale}>
        <Text style={type.caption}>{t.priceChart.low(fmtNum(min, 2), series.currency)}</Text>
        <Text style={type.caption}>{t.priceChart.high(fmtNum(max, 2), series.currency)}</Text>
      </View>
      <View style={styles.meta}>
        <Text style={[type.caption, { flexShrink: 1 }]}>{t.priceChart.note}</Text>
        {series.evidence_id ? <EvidenceChip id={series.evidence_id} runId={runId} /> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.sm },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: space.md },
  scale: { flexDirection: "row", justifyContent: "space-between" },
  meta: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: space.sm },
});

export default PriceChart;
