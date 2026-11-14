/**
 * Composant MoveCard — Carte d'une piste : nom, adéquation, justification courte, confiance, désaccord.
 */
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { fr } from "../i18n/fr";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { ExplanationItem } from "../types/contracts";
import { ClaimLine } from "./EvidenceChip";
import { ConfidenceBadge, FitBadge } from "./FitBadge";
import { Pill } from "./ui";

export function MoveCard({ item, rank, runId }: { item: ExplanationItem; rank: number; runId: string }) {
  const open = () => router.push({ pathname: "/piste/[ticker]", params: { ticker: item.ticker, run: runId } });
  return (
    <View style={styles.card}>
      <Pressable onPress={open} accessibilityRole="button" accessibilityLabel={`Ouvrir la fiche de ${item.name}`}>
        <View style={styles.head}>
          <Text style={styles.rank}>{rank}</Text>
          <View style={{ flex: 1 }}>
            <Text style={type.h3}>{item.name}</Text>
            <Text style={type.small}>
              {item.ticker} · {fr.assetClass[item.asset_class] ?? item.asset_class}
              {item.sector ? ` · ${item.sector}` : ""}
            </Text>
          </View>
          <Text style={styles.chevron}>›</Text>
        </View>
      </Pressable>
      <View style={styles.badges}>
        <FitBadge fit={item.fit} />
        <ConfidenceBadge confidence={item.confidence} />
        {item.debate_summary.dissent ? <Pill icon="⚖" text="Désaccord du débat" fg={colors.warn} bg={colors.warnBg} /> : null}
        {item.to_review ? <Pill icon="!" text="À examiner" fg={colors.bad} bg={colors.badBg} /> : null}
      </View>
      {item.why[0] ? <ClaimLine claim={item.why[0]} runId={runId} /> : null}
      <Pressable onPress={open} accessibilityRole="link" style={styles.more} hitSlop={8}>
        <Text style={styles.moreText}>Pourquoi ? Voir la fiche →</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border,
    padding: space.lg, gap: space.md,
  },
  head: { flexDirection: "row", alignItems: "center", gap: space.md },
  rank: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: colors.surfaceMuted, textAlign: "center",
    lineHeight: 32, fontWeight: "700", color: colors.text, overflow: "hidden",
  },
  chevron: { fontSize: 28, color: colors.textMuted },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  more: { minHeight: 32, justifyContent: "center" },
  moreText: { color: colors.primary, fontWeight: "600", fontSize: 15 },
});

export default MoveCard;
