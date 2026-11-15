/**
 * Écran : Pistes à explorer (accueil) — rappel du profil, progression de l'analyse, cartes,
 * « Écartées et pourquoi », état « Aucune recommandation », raccourcis, bouton flottant « Tester une idée ».
 */
import { Redirect, router } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { EvidenceChip } from "../../src/components/EvidenceChip";
import { Icon, type IconName } from "../../src/components/Icon";
import { MoveCard } from "../../src/components/MoveCard";
import { RunProgress } from "../../src/components/RunProgress";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, ErrorState, LinkText, Loading, Row, Screen, Section } from "../../src/components/ui";
import { fmtDate } from "../../src/format";
import { useBaseRun } from "../../src/hooks/useBaseRun";
import { useT } from "../../src/i18n";
import { useProfileStore } from "../../src/store/profile";
import { alpha, colors, radius, space } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";
import type { Explanation, RejectedItem } from "../../src/types/contracts";

export default function Pistes() {
  const t = useT();
  const { profileId, summary } = useProfileStore();
  const { runId, query, startError, restart } = useBaseRun(profileId);
  if (!profileId) return <Redirect href="/onboarding" />;
  const run = query.data;
  const result = run?.result ?? null;

  return (
    <View style={{ flex: 1 }}>
      <Screen>
        <View style={styles.profileCard}>
          <View style={styles.profileIcon}>
            <Icon name="user" size={20} color={colors.primaryText} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={type.eyebrow}>{t.pistes.yourProfile}</Text>
            <Text style={type.label} numberOfLines={2}>{summary}</Text>
            <Text style={type.caption}>{t.pistes.dataAsOf(fmtDate(run?.as_of ?? null))}</Text>
          </View>
          <LinkText label={t.pistes.changeProfile} icon={null} onPress={() => router.push("/(tabs)/profil")} />
        </View>

        {startError ? (
          <ErrorState error={startError} onRetry={restart} />
        ) : query.error ? (
          <ErrorState error={query.error} onRetry={restart} />
        ) : !run ? (
          <Loading label={t.common.launching} />
        ) : run.status === "en_cours" ? (
          <RunProgress steps={run.steps} />
        ) : run.status === "echec" ? (
          <ErrorState error={run.error ?? t.common.runFailed} onRetry={restart} />
        ) : result ? (
          <Results result={result} runId={runId!} />
        ) : null}

        {result ? (
          <Section title={t.pistes.exploreTitle}>
            <View style={styles.tiles}>
              <Tile icon="activity" label={t.common.runTrail} onPress={() => router.push({ pathname: "/run/[id]", params: { id: runId! } })} />
              <Tile icon="layers" label={t.pistes.compare} onPress={() => router.push("/comparer")} />
              <Tile icon="database" label={t.pistes.data} onPress={() => router.push("/donnees")} />
            </View>
            <Button label={t.pistes.rerun} variant="ghost" icon="refresh" onPress={restart} />
          </Section>
        ) : null}
      </Screen>

      <Pressable
        onPress={() => router.push("/(tabs)/tester")}
        accessibilityRole="button"
        accessibilityLabel={t.pistes.fab}
        style={({ pressed }) => [styles.fab, pressed && { opacity: 0.88, transform: [{ scale: 0.97 }] }]}
      >
        <Icon name="flask" size={20} color={colors.primaryText} />
        <Text style={styles.fabText}>{t.pistes.fab}</Text>
      </Pressable>
    </View>
  );
}

function Tile({ icon, label, onPress }: { icon: IconName; label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label}
      style={({ pressed }) => [styles.tile, pressed && { opacity: 0.8, transform: [{ scale: 0.98 }] }]}>
      <View style={styles.tileIcon}>
        <Icon name={icon} size={20} color={colors.mint} />
      </View>
      <Text style={styles.tileText} numberOfLines={2}>{label}</Text>
    </Pressable>
  );
}

function Results({ result, runId }: { result: Explanation; runId: string }) {
  const t = useT();
  if (result.no_recommendation) return <NoRecommendation result={result} runId={runId} />;
  return (
    <>
      <View style={{ gap: space.xs }}>
        <Text style={type.title} accessibilityRole="header">{result.headline}</Text>
        <Text style={type.small}>{t.pistes.resultsHint}</Text>
      </View>
      {result.items.map((item, i) => (
        <MoveCard key={item.ticker} item={item} rank={i + 1} runId={runId} />
      ))}
      <RejectedList rejected={result.rejected} runId={runId} />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function NoRecommendation({ result, runId }: { result: Explanation; runId: string }) {
  const t = useT();
  return (
    <>
      <Card style={{ borderColor: alpha(colors.warn, 0.4), backgroundColor: colors.warnBg }}>
        <Row>
          <Icon name="ban" size={22} color={colors.warn} />
          <Text style={[type.h2, { flex: 1 }]} accessibilityRole="header">{t.pistes.noRecoTitle}</Text>
        </Row>
        <Text style={type.body}>{t.pistes.noRecoBody}</Text>
        {result.missing.map((m) => (
          <Text key={m} style={type.body}>• {m}</Text>
        ))}
        <Text style={type.small}>{t.pistes.noRecoValid}</Text>
        <Button label={t.pistes.reviewRules} variant="secondary" onPress={() => router.push("/(tabs)/profil")} />
      </Card>
      <RejectedList rejected={result.rejected} runId={runId} initiallyOpen />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function RejectedList({ rejected, runId, initiallyOpen = false }: { rejected: RejectedItem[]; runId: string; initiallyOpen?: boolean }) {
  const t = useT();
  const [open, setOpen] = useState(initiallyOpen);
  if (rejected.length === 0) return null;
  const rules = rejected.filter((r) => r.kind === "contrainte");
  const ranked = rejected.filter((r) => r.kind !== "contrainte");
  return (
    <Section
      title={t.pistes.rejectedTitle(rejected.length)}
      right={
        <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }} hitSlop={10}
          style={({ pressed }) => [styles.toggle, pressed && { opacity: 0.75 }]}>
          <Text style={styles.toggleText}>{open ? t.pistes.fold : t.pistes.unfold}</Text>
          <Icon name={open ? "chevronUp" : "chevronDown"} size={16} color={colors.mint} />
        </Pressable>
      }
    >
      {open ? (
        <View style={{ gap: space.md }}>
          {rules.length > 0 ? <RejectedGroup title={t.pistes.rejectedByRule} items={rules} runId={runId} icon="ban" color={colors.bad} /> : null}
          {ranked.length > 0 ? <RejectedGroup title={t.pistes.rejectedRanked} items={ranked} runId={runId} icon="trendingDown" color={colors.warn} /> : null}
        </View>
      ) : null}
    </Section>
  );
}

function RejectedGroup({ title, items, runId, icon, color }: { title: string; items: RejectedItem[]; runId: string; icon: IconName; color: string }) {
  const t = useT();
  return (
    <Card>
      <Row>
        <Icon name={icon} size={18} color={color} />
        <Text style={[type.h3, { flex: 1 }]}>{title}</Text>
      </Row>
      {items.map((r) => (
        <View key={r.ticker} style={styles.rejRow}>
          <Text style={[type.label, { color }]}>{r.ticker}</Text>
          <Text style={type.body}>{r.reason}</Text>
          <Row>
            {(r.evidence_ids ?? []).map((id) => <EvidenceChip key={id} id={id} runId={runId} />)}
            <LinkText label={t.common.seeSheetArrow} onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: r.ticker, run: runId } })} />
          </Row>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  profileCard: {
    flexDirection: "row", alignItems: "center", gap: space.md, padding: space.lg, borderRadius: radius.lg,
    backgroundColor: alpha(colors.mint, 0.06), borderWidth: 1, borderColor: colors.borderStrong,
  },
  profileIcon: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  tiles: { flexDirection: "row", gap: space.sm },
  tile: {
    flex: 1, minHeight: 96, padding: space.md, gap: space.sm, borderRadius: radius.lg, justifyContent: "space-between",
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  tileIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center" },
  tileText: { fontFamily, fontSize: 14, fontWeight: "700", color: colors.text },
  toggle: {
    flexDirection: "row", alignItems: "center", gap: 4, minHeight: 36, paddingHorizontal: space.md,
    borderRadius: radius.pill, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  toggleText: { fontFamily, color: colors.mint, fontWeight: "700", fontSize: 14 },
  rejRow: { gap: space.xs, paddingVertical: space.sm, borderTopWidth: 1, borderTopColor: alpha(colors.mint, 0.07) },
  fab: {
    position: "absolute", right: space.lg, bottom: space.lg, backgroundColor: colors.mint, flexDirection: "row", alignItems: "center", gap: space.sm,
    borderRadius: radius.pill, paddingHorizontal: space.xl, paddingVertical: space.md, minHeight: 54,
    shadowColor: colors.mint, shadowOpacity: 0.35, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 8,
  },
  fabText: { fontFamily, color: colors.primaryText, fontWeight: "800", fontSize: 16 },
});
