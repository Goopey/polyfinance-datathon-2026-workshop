/**
 * Composant MoveCard — Carte d'une piste : rang, nom, adéquation, confiance, désaccord, justification courte.
 * Une bande de couleur à gauche reprend l'adéquation (doublée par la pastille, jamais seule).
 */
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import type { ExplanationItem } from "../types/contracts";
import { ClaimLine } from "./EvidenceChip";
import { ConfidenceBadge, FitBadge } from "./FitBadge";
import { Icon } from "./Icon";
import { LinkText, Pill } from "./ui";

const ACCENT = { "élevée": colors.good, partielle: colors.warn, faible: colors.bad } as const;

export function MoveCard({ item, rank, runId }: { item: ExplanationItem; rank: number; runId: string }) {
  const t = useT();
  const open = () => router.push({ pathname: "/piste/[ticker]", params: { ticker: item.ticker, run: runId } });
  return (
    <View style={styles.card}>
      <View style={[styles.accent, { backgroundColor: ACCENT[item.fit] }]} />
      <Pressable onPress={open} accessibilityRole="button" accessibilityLabel={t.common.openSheetOf(item.name)}
        style={({ pressed }) => pressed && { opacity: 0.8 }}>
        <View style={styles.head}>
          <View style={[styles.rank, rank === 1 && styles.rankFirst]}>
            <Text style={[styles.rankText, rank === 1 && { color: colors.primaryText }]}>{rank}</Text>
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={type.h3}>{item.name}</Text>
            <Text style={type.small}>
              {item.ticker} · {t.assetClass[item.asset_class] ?? item.asset_class}
              {item.sector ? ` · ${item.sector}` : ""}
            </Text>
          </View>
          <Icon name="chevronRight" size={22} color={colors.textMuted} />
        </View>
      </Pressable>
      <View style={styles.badges}>
        <FitBadge fit={item.fit} />
        <ConfidenceBadge confidence={item.confidence} />
        {item.debate_summary.dissent ? <Pill icon="scale" text={t.pistes.dissent} fg={colors.warn} bg={colors.warnBg} /> : null}
        {item.to_review ? <Pill icon="alert" text={t.pistes.toReview} fg={colors.bad} bg={colors.badBg} /> : null}
      </View>
      {item.why[0] ? <ClaimLine claim={item.why[0]} runId={runId} /> : null}
      <View style={styles.footer}>
        <LinkText label={t.pistes.whyLink} onPress={open} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border,
    padding: space.lg, paddingLeft: space.lg + 6, gap: space.md, overflow: "hidden",
    shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 3,
  },
  accent: { position: "absolute", left: 0, top: 0, bottom: 0, width: 4 },
  head: { flexDirection: "row", alignItems: "center", gap: space.md },
  rank: {
    width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center",
    backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: colors.borderStrong,
  },
  rankFirst: { backgroundColor: colors.mint, borderColor: colors.mint },
  rankText: { fontFamily, fontWeight: "800", fontSize: 15, color: colors.mint },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  footer: { borderTopWidth: 1, borderTopColor: alpha(colors.mint, 0.08), paddingTop: space.sm },
});

export default MoveCard;
