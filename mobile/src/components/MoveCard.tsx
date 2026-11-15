/**
 * Composant MoveCard — Carte d'une piste : rang, nom, score sur 100, adéquation, confiance, désaccord,
 * justification courte. Toute la carte ouvre la fiche ; la flèche en haut à droite l'indique.
 * Une bande de couleur à gauche reprend l'adéquation (doublée par la pastille, jamais seule).
 */
import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { useTx } from "../i18n/data";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import { CRITERIA, type ExplanationItem } from "../types/contracts";
import { ConfidenceBadge, FitBadge } from "./FitBadge";
import { Icon } from "./Icon";
import { Pill, Tap } from "./ui";

const ACCENT = { "élevée": colors.good, partielle: colors.warn, faible: colors.bad } as const;

export function MoveCard({ item, rank, runId }: { item: ExplanationItem; rank: number; runId: string }) {
  const t = useT();
  const tx = useTx();
  const open = () => router.push({ pathname: "/piste/[ticker]", params: { ticker: item.ticker, run: runId } });
  const score = Math.round(CRITERIA.reduce((s, k) => s + (item.contributions[k] ?? 0), 0) * 100);
  return (
    <Tap onPress={open} scaleTo={0.975} accessibilityRole="button" accessibilityLabel={t.common.openSheetOf(item.name)}
      style={({ pressed, hovered }) => [styles.card, (pressed || hovered) && styles.cardActive]}>
      <View style={[styles.accent, { backgroundColor: ACCENT[item.fit] }]} />
      <View style={styles.head}>
        <View style={[styles.rank, rank === 1 && styles.rankFirst]}>
          <Text style={[styles.rankText, rank === 1 && { color: colors.primaryText }]}>{rank}</Text>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={type.h3}>{item.name}</Text>
          <Text style={type.small}>
            {item.ticker} · {t.assetClass[item.asset_class] ?? item.asset_class}
            {item.sector ? ` · ${tx(item.sector)}` : ""}
          </Text>
        </View>
        <View style={styles.arrow}>
          <Icon name="arrowRight" size={18} color={colors.primaryText} strokeWidth={2.4} />
        </View>
      </View>
      <View style={styles.scoreRow}>
        <View style={styles.scoreTrack}>
          <View style={[styles.scoreFill, { width: `${Math.max(0, Math.min(100, score))}%`, backgroundColor: ACCENT[item.fit] }]} />
        </View>
        <Text style={styles.scoreText}>{t.pistes.score(score)}</Text>
      </View>
      <View style={styles.badges}>
        <FitBadge fit={item.fit} />
        <ConfidenceBadge confidence={item.confidence} />
        {item.debate_summary.dissent ? <Pill icon="scale" text={t.pistes.dissent} fg={colors.warn} bg={colors.warnBg} /> : null}
        {item.to_review ? <Pill icon="alert" text={t.pistes.toReview} fg={colors.bad} bg={colors.badBg} /> : null}
      </View>
      {item.why[0] ? <Text style={[type.body, { color: colors.textMuted }]} numberOfLines={3}>{tx(item.why[0].text)}</Text> : null}
    </Tap>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border,
    padding: space.lg, paddingLeft: space.lg + 6, gap: space.md, overflow: "hidden",
    shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 3,
  },
  cardActive: { borderColor: colors.borderStrong, backgroundColor: colors.surfaceMuted },
  accent: { position: "absolute", left: 0, top: 0, bottom: 0, width: 4 },
  head: { flexDirection: "row", alignItems: "center", gap: space.md },
  rank: {
    width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center",
    backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: colors.borderStrong,
  },
  rankFirst: { backgroundColor: colors.mint, borderColor: colors.mint },
  rankText: { fontFamily, fontWeight: "800", fontSize: 15, color: colors.mint },
  arrow: { width: 34, height: 34, borderRadius: 17, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  scoreRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  scoreTrack: { flex: 1, height: 6, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, overflow: "hidden" },
  scoreFill: { height: 6, borderRadius: radius.pill },
  scoreText: { fontFamily, fontSize: 13, fontWeight: "800", color: colors.text, minWidth: 54, textAlign: "right" },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
});

export default MoveCard;
