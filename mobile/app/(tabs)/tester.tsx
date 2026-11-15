/**
 * Écran : Tester une idée — l'utilisateur choisit un titre ; le système dit s'il est cohérent avec le profil
 * et pourquoi : verdict, tensions chiffrées, effet sur le panier, alternatives étayées (test Robert).
 * Le titre demandé est toujours analysé, jamais filtré en silence.
 */
import { useQuery } from "@tanstack/react-query";
import { Redirect, router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { listAssets } from "../../src/api/assets";
import { startRun, useRun } from "../../src/api/runs";
import { ClaimLine } from "../../src/components/EvidenceChip";
import { Icon, type IconName } from "../../src/components/Icon";
import { RunProgress } from "../../src/components/RunProgress";
import { Button, Card, ErrorState, Loading, Row, Screen, Section } from "../../src/components/ui";
import { useT } from "../../src/i18n";
import { useProfileStore } from "../../src/store/profile";
import { alpha, colors, radius, space, touchMin } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";
import type { CoherenceAnalysis, Verdict } from "../../src/types/contracts";

const VERDICT: Record<Verdict, { icon: IconName; fg: string; bg: string }> = {
  "cohérent": { icon: "check", fg: colors.good, bg: colors.goodBg },
  "cohérent avec réserve": { icon: "alert", fg: colors.warn, bg: colors.warnBg },
  "incohérent avec le profil": { icon: "x", fg: colors.bad, bg: colors.badBg },
};

export default function TesterIdee() {
  const t = useT();
  const { profileId, label } = useProfileStore();
  const [search, setSearch] = useState("");
  const [focused, setFocused] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [startError, setStartError] = useState<unknown>(null);
  const assets = useQuery({ queryKey: ["assets"], queryFn: listAssets });
  const run = useRun(runId);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    return (assets.data ?? []).filter((a) => !s || a.ticker.toLowerCase().includes(s) || a.name.toLowerCase().includes(s));
  }, [assets.data, search]);

  if (!profileId) return <Redirect href="/onboarding" />;

  const test = async (ticker: string) => {
    setStartError(null);
    try {
      const { run_id } = await startRun({ profile_id: profileId, requested_ticker: ticker });
      setRunId(run_id);
    } catch (e) {
      setStartError(e);
    }
  };
  const reset = () => {
    setRunId(null);
    setSearch("");
  };

  const status = run.data;
  const coherence = status?.result?.coherence ?? null;

  return (
    <Screen>
      {!runId ? (
        <>
          <View style={{ gap: space.sm }}>
            <Text style={type.title} accessibilityRole="header">{t.tester.title}</Text>
            <Text style={[type.body, { color: colors.textMuted }]}>{t.tester.body(label)}</Text>
          </View>
          <View style={[styles.search, focused && styles.searchFocus]}>
            <Icon name="search" size={20} color={focused ? colors.mint : colors.textMuted} />
            <TextInput
              value={search}
              onChangeText={setSearch}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder={t.tester.placeholder}
              placeholderTextColor={colors.textSubtle}
              style={styles.input}
              accessibilityLabel={t.tester.searchA11y}
              autoCapitalize="characters"
            />
          </View>
          {startError ? <ErrorState error={startError} /> : null}
          {assets.isLoading ? <Loading /> : assets.error ? <ErrorState error={assets.error} onRetry={() => assets.refetch()} /> : null}
          <View style={{ gap: space.sm }}>
            {filtered.map((a) => (
              <Pressable key={a.ticker} onPress={() => test(a.ticker)} accessibilityRole="button" accessibilityLabel={t.tester.testA11y(a.name)}
                style={({ pressed }) => [styles.assetRow, pressed && { opacity: 0.8, transform: [{ scale: 0.99 }] }]}>
                <View style={styles.ticker}>
                  <Text style={styles.tickerText} numberOfLines={1}>{a.ticker.slice(0, 4)}</Text>
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={type.h3}>{a.name}</Text>
                  <Text style={type.small}>{a.ticker} · {t.assetClass[a.asset_class] ?? a.asset_class}{a.sector ? ` · ${a.sector}` : ""}</Text>
                </View>
                <Icon name="chevronRight" size={22} color={colors.textMuted} />
              </Pressable>
            ))}
            {assets.data && filtered.length === 0 ? <Text style={type.body}>{t.tester.noMatch}</Text> : null}
          </View>
        </>
      ) : run.error ? (
        <ErrorState error={run.error} onRetry={reset} />
      ) : !status || status.status === "en_cours" ? (
        status ? <RunProgress steps={status.steps} /> : <Loading label={t.common.launching} />
      ) : coherence ? (
        <CoherenceView c={coherence} runId={runId} />
      ) : (
        <ErrorState error={status.error ?? t.tester.missing} onRetry={reset} />
      )}

      {runId && status?.status !== "en_cours" ? <Button label={t.tester.another} variant="secondary" icon="search" onPress={reset} /> : null}
    </Screen>
  );
}

function CoherenceView({ c, runId }: { c: CoherenceAnalysis; runId: string }) {
  const t = useT();
  const v = VERDICT[c.verdict];
  return (
    <>
      <View style={{ gap: space.xs }}>
        <Text style={type.eyebrow}>{t.tester.eyebrow}</Text>
        <Text style={type.title}>{c.name}</Text>
      </View>
      <View style={[styles.verdict, { backgroundColor: v.bg, borderColor: alpha(v.fg, 0.5) }]} accessibilityRole="summary">
        <Row style={{ flexWrap: "nowrap" }}>
          <View style={[styles.verdictIcon, { backgroundColor: v.fg }]}>
            <Icon name={v.icon} size={20} color={colors.primaryText} strokeWidth={3} />
          </View>
          <Text style={[styles.verdictText, { color: v.fg }]}>{t.verdict[c.verdict]}</Text>
        </Row>
        <Text style={type.small}>{t.tester.verdictNote}</Text>
      </View>

      <Section title={t.tester.tensions(c.tensions.length)}>
        <Card style={{ gap: space.md }}>
          {c.tensions.length === 0 ? (
            <Text style={type.body}>{t.tester.noTension}</Text>
          ) : (
            c.tensions.map((x) => <ClaimLine key={x.text} claim={x} runId={runId} />)
          )}
        </Card>
      </Section>

      {c.context.length > 0 ? (
        <Section title={t.tester.context}>
          <Card style={{ backgroundColor: colors.scenarioBg, borderColor: alpha(colors.scenario, 0.3), gap: space.md }}>
            {c.context.map((x) => <ClaimLine key={x.text} claim={x} runId={runId} />)}
          </Card>
        </Section>
      ) : null}

      {c.alternatives.length > 0 ? (
        <Section title={t.tester.alternatives}>
          {c.alternatives.map((alt) => (
            <Card key={alt.ticker}>
              <Text style={type.h3}>{alt.name}</Text>
              <ClaimLine claim={alt.why} runId={runId} />
              <Button label={t.common.seeSheet} variant="ghost" icon="arrowRight"
                onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: alt.ticker, run: runId } })} />
            </Card>
          ))}
        </Section>
      ) : null}

      <Button label={t.common.seeSheetOf(c.name)} variant="primary" icon="arrowRight"
        onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: c.ticker, run: runId } })} />
      <Button label={t.common.runTrail} variant="ghost" icon="activity" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runId } })} />
    </>
  );
}

const styles = StyleSheet.create({
  search: {
    flexDirection: "row", alignItems: "center", gap: space.sm, minHeight: touchMin + 8,
    borderWidth: 1.5, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: space.lg, backgroundColor: colors.surface,
  },
  searchFocus: { borderColor: colors.primary },
  input: { flex: 1, minHeight: touchMin, fontSize: 16, color: colors.text, fontFamily, outlineStyle: "none" } as object,
  assetRow: {
    flexDirection: "row", alignItems: "center", gap: space.md, backgroundColor: colors.surface, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border, padding: space.md, minHeight: touchMin + 16,
  },
  ticker: { width: 46, height: 46, borderRadius: 14, backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center" },
  tickerText: { fontFamily, fontSize: 11, fontWeight: "800", color: colors.mint, letterSpacing: 0.4 },
  verdict: { borderWidth: 1.5, borderRadius: radius.lg, padding: space.lg, gap: space.md },
  verdictIcon: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  verdictText: { fontFamily, fontSize: 21, fontWeight: "800", flex: 1, letterSpacing: -0.2 },
});
