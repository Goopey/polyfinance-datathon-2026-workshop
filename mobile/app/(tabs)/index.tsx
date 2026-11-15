/**
 * Écran : Pistes à explorer (accueil) — rappel du profil, progression de l'analyse, cartes,
 * « Écartées et pourquoi », état « Aucune recommandation », raccourcis, bouton flottant « Tester une idée ».
 */
import { useMutation } from "@tanstack/react-query";
import { Redirect, router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { isNotFound } from "../../src/api/client";
import { createProfile } from "../../src/api/profiles";
import { EvidenceChip } from "../../src/components/EvidenceChip";
import { Icon, type IconName } from "../../src/components/Icon";
import { MoveCard } from "../../src/components/MoveCard";
import { RunProgress } from "../../src/components/RunProgress";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, Collapsible, ErrorState, FadeIn, LinkText, Loading, Row, Screen, Section, Tap } from "../../src/components/ui";
import { fmtDate } from "../../src/format";
import { useBaseRun } from "../../src/hooks/useBaseRun";
import { useT } from "../../src/i18n";
import { useTx } from "../../src/i18n/data";
import { useProfileStore } from "../../src/store/profile";
import { alpha, colors, radius, space } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";
import { blockingCriterion, stripNoRecoPrefix } from "../../src/noRecommendation";
import type { Criterion, Explanation, RejectedItem } from "../../src/types/contracts";

export default function Pistes() {
  const t = useT();
  const tx = useTx();
  const { profileId, summary, reset } = useProfileStore();
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
            <Text style={type.label} numberOfLines={2}>{summary ? tx(summary) : ""}</Text>
            <Text style={type.caption}>{t.pistes.dataAsOf(fmtDate(run?.as_of ?? null))}</Text>
          </View>
          <LinkText label={t.pistes.changeProfile} icon={null} onPress={() => router.push("/(tabs)/profil")} />
        </View>

        {startError && isNotFound(startError) ? (
          // Profil créé avant un redémarrage de l'API (gardé en mémoire côté serveur) : il n'existe plus.
          <Card style={{ borderColor: alpha(colors.warn, 0.4), backgroundColor: colors.warnBg }}>
            <Row>
              <Icon name="alert" size={20} color={colors.warn} />
              <Text style={[type.h3, { flex: 1 }]}>{t.pistes.profileLostTitle}</Text>
            </Row>
            <Text style={type.body}>{t.pistes.profileLostBody}</Text>
            <Button label={t.profil.change} icon="refresh" onPress={() => { reset(); router.replace("/onboarding"); }} />
          </Card>
        ) : startError ? (
          <ErrorState error={startError} onRetry={restart} />
        ) : query.error ? (
          <ErrorState error={query.error} onRetry={restart} />
        ) : !run ? (
          <Loading label={t.common.launching} />
        ) : run.status === "en_cours" ? (
          <RunProgress steps={run.steps} />
        ) : run.status === "echec" ? (
          <ErrorState error={run.error ? tx(run.error) : t.common.runFailed} onRetry={restart} />
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

      <Tap
        onPress={() => router.push("/(tabs)/tester")}
        accessibilityRole="button"
        accessibilityLabel={t.pistes.fab}
        scaleTo={0.93}
        style={({ hovered }) => [styles.fab, hovered && { shadowOpacity: 0.6 }]}
      >
        <Icon name="flask" size={20} color={colors.primaryText} />
        <Text style={styles.fabText}>{t.pistes.fab}</Text>
      </Tap>
    </View>
  );
}

function Tile({ icon, label, onPress }: { icon: IconName; label: string; onPress: () => void }) {
  return (
    <Tap onPress={onPress} accessibilityRole="button" accessibilityLabel={label} scaleTo={0.95}
      style={({ pressed, hovered }) => [styles.tile, (pressed || hovered) && styles.tileActive]}>
      <View style={styles.tileIcon}>
        <Icon name={icon} size={20} color={colors.mint} />
      </View>
      <Text style={styles.tileText} numberOfLines={2}>{label}</Text>
    </Tap>
  );
}

function Results({ result, runId }: { result: Explanation; runId: string }) {
  const tx = useTx();
  if (result.no_recommendation) return <NoRecommendation result={result} runId={runId} />;
  return (
    <>
      <FadeIn>
        <Text style={type.title} accessibilityRole="header">{tx(result.headline)}</Text>
      </FadeIn>
      {result.items.map((item, i) => (
        <FadeIn key={item.ticker} index={i + 1}>
          <MoveCard item={item} rank={i + 1} runId={runId} />
        </FadeIn>
      ))}
      <RejectedList rejected={result.rejected} runId={runId} />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function NoRecommendation({ result, runId }: { result: Explanation; runId: string }) {
  const t = useT();
  const tx = useTx();
  const { profileId, setProfile } = useProfileStore();
  // Critère prioritaire sans donnée (ex. ESG pour Mateo) : on propose de le retirer, sur demande explicite.
  const blocking = result.missing.map(blockingCriterion).find((c): c is Criterion => c !== null) ?? null;
  const without = useMutation({
    mutationFn: () => createProfile({
      base_persona: profileId!, objectif: "equilibre", horizon: "moyen", tolerance: "moderee",
      preferences: [], exclusions: [], weights_override: { [blocking!]: 0 },
    }),
    onSuccess: (pw) => setProfile(pw),
  });
  return (
    <>
      <Card style={{ borderColor: alpha(colors.warn, 0.4), backgroundColor: colors.warnBg, gap: space.md }}>
        <Row>
          <Icon name="ban" size={22} color={colors.warn} />
          <Text style={[type.h2, { flex: 1 }]} accessibilityRole="header">{t.pistes.noRecoTitle}</Text>
        </Row>
        <View style={{ gap: space.xs }}>
          <Text style={type.body}>{t.pistes.noRecoBody}</Text>
          {result.missing.map((m) => (
            <Text key={m} style={type.body}>• {tx(stripNoRecoPrefix(m))}</Text>
          ))}
        </View>
        {without.error ? <ErrorState error={without.error} onRetry={() => without.mutate()} /> : null}
        {blocking && profileId ? (
          <View style={{ gap: space.xs }}>
            <Button
              label={without.isPending ? t.common.launching : t.pistes.withoutCriterion(t.criteria[blocking])}
              icon={without.isPending ? undefined : "arrowRight"}
              disabled={without.isPending}
              onPress={() => without.mutate()}
            />
            <Text style={[type.caption, { textAlign: "center" }]}>{t.pistes.withoutCriterionHint}</Text>
          </View>
        ) : null}
        {profileId ? (
          <Button label={t.pistes.adjustWeights} variant="secondary" icon="sliders"
            onPress={() => router.push({ pathname: "/onboarding/resume", params: { id: profileId } })} />
        ) : null}
      </Card>
      <RejectedList rejected={result.rejected} runId={runId} initiallyOpen />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function RejectedList({ rejected, runId, initiallyOpen = false }: { rejected: RejectedItem[]; runId: string; initiallyOpen?: boolean }) {
  const t = useT();
  if (rejected.length === 0) return null;
  const rules = rejected.filter((r) => r.kind === "contrainte");
  const ranked = rejected.filter((r) => r.kind !== "contrainte");
  return (
    <Collapsible title={t.pistes.rejectedTitle(rejected.length)} summary={t.pistes.rejectedSummary(rules.length, ranked.length)}
      icon="ban" accent={colors.bad} initiallyOpen={initiallyOpen}>
      {rules.length > 0 ? <RejectedGroup title={t.pistes.rejectedByRule} items={rules} runId={runId} icon="ban" color={colors.bad} /> : null}
      {ranked.length > 0 ? <RejectedGroup title={t.pistes.rejectedRanked} items={ranked} runId={runId} icon="trendingDown" color={colors.warn} /> : null}
    </Collapsible>
  );
}

function RejectedGroup({ title, items, runId, icon, color }: { title: string; items: RejectedItem[]; runId: string; icon: IconName; color: string }) {
  const t = useT();
  const tx = useTx();
  return (
    <View style={{ gap: space.sm }}>
      <Row>
        <Icon name={icon} size={16} color={color} />
        <Text style={[type.label, { flex: 1, color }]}>{title}</Text>
      </Row>
      {items.map((r) => (
        <Tap key={r.ticker} scaleTo={0.98} accessibilityRole="button"
          onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: r.ticker, run: runId } })}
          style={({ pressed, hovered }) => [styles.rejRow, (pressed || hovered) && styles.rejRowActive]}>
          <View style={{ flex: 1, gap: 4 }}>
            <Text style={type.h3}>{r.ticker}</Text>
            <Text style={type.small}>{tx(r.reason)}</Text>
            <Row>{(r.evidence_ids ?? []).map((id, i, all) => (
              <EvidenceChip key={id} id={id} runId={runId} label={all.length > 1 ? t.common.sourceN(i + 1) : undefined} />
            ))}</Row>
          </View>
          <Icon name="chevronRight" size={20} color={colors.textMuted} />
        </Tap>
      ))}
    </View>
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
  tileActive: { borderColor: colors.primary, backgroundColor: colors.surfaceMuted },
  tileIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center" },
  tileText: { fontFamily, fontSize: 14, fontWeight: "700", color: colors.text },
  rejRow: {
    flexDirection: "row", alignItems: "center", gap: space.md, padding: space.md, borderRadius: radius.md,
    backgroundColor: colors.surfaceMuted, borderWidth: 1, borderColor: colors.border,
  },
  rejRowActive: { borderColor: colors.borderStrong },
  fab: {
    position: "absolute", right: space.lg, bottom: space.lg, backgroundColor: colors.mint, flexDirection: "row", alignItems: "center", gap: space.sm,
    borderRadius: radius.pill, paddingHorizontal: space.xl, paddingVertical: space.md, minHeight: 54,
    shadowColor: colors.mint, shadowOpacity: 0.35, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 8,
  },
  fabText: { fontFamily, color: colors.primaryText, fontWeight: "800", fontSize: 16 },
});
