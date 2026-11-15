/**
 * Composant SentimentGauge — Sentiment du dernier mois publié : recommandations d'analystes et indice
 * des initiés (actions seulement). Affichage seulement : n'entre ni dans le score ni dans la décision.
 * Conception : docs/07_UX_UI.md ; données : AssetSheet.sentiment (Finnhub, docs/04_DONNEES.md §11).
 */
import { StyleSheet, Text, View } from "react-native";
import { fmtMonth, fmtNum, fmtPct } from "../format";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { AnalystSentiment, SentimentLabel, SentimentView } from "../types/contracts";
import { EvidenceChip } from "./EvidenceChip";
import { Pill } from "./ui";

const TONE: Record<SentimentLabel, { fg: string; bg: string; icon: string }> = {
  positif: { fg: colors.good, bg: colors.goodBg, icon: "check" },
  neutre: { fg: colors.neutral, bg: colors.neutralBg, icon: "minus" },
  négatif: { fg: colors.bad, bg: colors.badBg, icon: "alert" },
};

const BUCKETS: { key: keyof Pick<AnalystSentiment, "strong_buy" | "buy" | "hold" | "sell" | "strong_sell">; color: string }[] = [
  { key: "strong_buy", color: colors.good },
  { key: "buy", color: alpha(colors.good, 0.55) },
  { key: "hold", color: alpha(colors.mint, 0.35) },
  { key: "sell", color: alpha(colors.bad, 0.55) },
  { key: "strong_sell", color: colors.bad },
];

export function SentimentGauge({ sentiment, runId }: { sentiment: SentimentView | null; runId?: string | null }) {
  const t = useT();
  if (!sentiment) return null; // FNB et crypto : pas de donnée, la fiche masque la section
  const tone = TONE[sentiment.label];
  const a = sentiment.analysts;
  const total = a ? BUCKETS.reduce((s, b) => s + a[b.key], 0) : 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <Pill text={t.sentiment.label[sentiment.label]} fg={tone.fg} bg={tone.bg} icon={tone.icon} />
        {a && total > 0 ? <Text style={type.small}>{t.sentiment.total(total)}</Text> : null}
      </View>

      {a && total > 0 ? (
        <View style={styles.block}>
          <Text style={type.label}>{t.sentiment.analysts(fmtMonth(a.period))}</Text>
          <View style={styles.bar} accessible accessibilityLabel={t.sentiment.a11y(a.strong_buy + a.buy, a.hold, a.sell + a.strong_sell)}>
            {BUCKETS.filter((b) => a[b.key] > 0).map((b) => (
              <View key={b.key} style={{ flex: a[b.key], backgroundColor: b.color }} />
            ))}
          </View>
          <View style={styles.legend}>
            {BUCKETS.filter((b) => a[b.key] > 0).map((b) => (
              <View key={b.key} style={styles.legendItem}>
                <View style={[styles.swatch, { backgroundColor: b.color }]} />
                <Text style={type.caption}>{`${t.sentiment.bucket[b.key]} ${a[b.key]} (${fmtPct((a[b.key] / total) * 100, 0)})`}</Text>
              </View>
            ))}
          </View>
          <View style={styles.row}>
            <Text style={type.small}>{t.sentiment.balance(fmtNum(a.balance, 2))}</Text>
            <EvidenceChip id={a.evidence_id} runId={runId} />
          </View>
        </View>
      ) : null}

      {sentiment.insiders ? (
        <View style={styles.block}>
          <Text style={type.label}>{t.sentiment.insiders(fmtMonth(sentiment.insiders.period))}</Text>
          <View style={styles.track}>
            <View style={styles.mid} />
            <View style={[styles.marker, { left: `${((Math.max(-100, Math.min(100, sentiment.insiders.mspr)) + 100) / 200) * 100}%` }]} />
          </View>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <Text style={type.caption}>−100 · {t.sentiment.selling}</Text>
            <Text style={type.caption}>0</Text>
            <Text style={type.caption}>{t.sentiment.buying} · +100</Text>
          </View>
          <View style={styles.row}>
            <Text style={type.small}>{t.sentiment.mspr(fmtNum(sentiment.insiders.mspr, 1))}</Text>
            <EvidenceChip id={sentiment.insiders.evidence_id} runId={runId} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.md },
  block: { gap: space.xs + 2 },
  row: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: space.sm },
  bar: { flexDirection: "row", height: 12, borderRadius: radius.pill, overflow: "hidden", backgroundColor: colors.surfaceRaised },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: space.md },
  legendItem: { flexDirection: "row", alignItems: "center", gap: space.xs },
  swatch: { width: 10, height: 10, borderRadius: 3 },
  track: { height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, justifyContent: "center" },
  mid: { position: "absolute", left: "50%", width: 2, height: 14, marginLeft: -1, backgroundColor: alpha(colors.mint, 0.4) },
  marker: {
    position: "absolute", width: 16, height: 16, borderRadius: 8, marginLeft: -8,
    backgroundColor: colors.mint, borderWidth: 3, borderColor: colors.bg,
  },
});

export default SentimentGauge;
