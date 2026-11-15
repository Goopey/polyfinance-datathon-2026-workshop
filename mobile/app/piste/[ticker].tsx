/**
 * Écran : Fiche d'une piste — dans l'ordre : aperçu, graphe de dépendances, risque, débat, signaux,
 * pourquoi ce classement, ce que nous ne savons pas. Conception : docs/07_UX_UI.md §3.
 * Paramètres : `ticker`, `run` (facultatif : l'analyse dont la piste est issue).
 */
import { useQuery } from "@tanstack/react-query";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";
import { getAsset, getGraph } from "../../src/api/assets";
import { getProfile } from "../../src/api/profiles";
import { useRun } from "../../src/api/runs";
import { ContributionBars } from "../../src/components/ContributionBars";
import { DebateSummary } from "../../src/components/DebateSummary";
import { ClaimLine, EvidenceChip } from "../../src/components/EvidenceChip";
import { ConfidenceBadge, FitBadge } from "../../src/components/FitBadge";
import { Icon } from "../../src/components/Icon";
import { RiskMeter } from "../../src/components/RiskMeter";
import { SupplyChainGraph } from "../../src/components/SupplyChainGraph";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../../src/components/ui";
import { useT } from "../../src/i18n";
import { useProfileStore } from "../../src/store/profile";
import { useSettings } from "../../src/store/settings";
import { alpha, colors, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";

export default function FichePiste() {
  const t = useT();
  const { ticker, run: runParam } = useLocalSearchParams<{ ticker: string; run?: string }>();
  const currentProfile = useProfileStore((s) => s.profileId);
  const advanced = useSettings((s) => s.mode === "avance");
  const run = useRun(runParam);
  const profileId = run.data?.profile_id ?? currentProfile ?? undefined;
  const sheet = useQuery({ queryKey: ["asset", ticker, profileId, runParam], queryFn: () => getAsset(ticker!, { profileId, runId: runParam }), enabled: !!ticker });
  const graph = useQuery({ queryKey: ["graph", ticker, runParam], queryFn: () => getGraph(ticker!, runParam), enabled: !!ticker });
  const profile = useQuery({ queryKey: ["profile", profileId], queryFn: () => getProfile(profileId!), enabled: !!profileId });

  if (sheet.isLoading || (runParam && run.isLoading)) return <Loading />;
  if (sheet.error) return <Screen><ErrorState error={sheet.error} onRetry={() => sheet.refetch()} /></Screen>;
  const a = sheet.data!;
  const result = run.data?.result ?? null;
  const item = result?.items.find((i) => i.ticker === ticker) ?? null;
  const rejected = result?.rejected.find((r) => r.ticker === ticker) ?? null;
  const metrics = a.metrics.filter((m) => advanced || !m.advanced);

  return (
    <Screen>
      <Stack.Screen options={{ title: a.name }} />

      {/* 1. Aperçu */}
      <View style={{ gap: space.sm }}>
        <Text style={type.eyebrow}>
          {a.ticker} · {t.assetClass[a.asset_class] ?? a.asset_class}
        </Text>
        <Text style={type.display}>{a.name}</Text>
        <Text style={type.small}>
          {a.sector ? `${a.sector} · ` : ""}{t.fiche.listed(a.currency)}
        </Text>
        {item ? (
          <Row style={{ marginTop: space.xs }}>
            <FitBadge fit={item.fit} />
            <ConfidenceBadge confidence={item.confidence} />
            {item.to_review ? <Pill icon="alert" text={t.pistes.toReview} fg={colors.bad} bg={colors.badBg} /> : null}
          </Row>
        ) : null}
      </View>
      {item ? (
        <Card style={{ gap: space.md }}>
          <Text style={type.h3}>{t.fiche.whyThis}</Text>
          {item.why.map((c) => <ClaimLine key={c.text} claim={c} runId={runParam} />)}
        </Card>
      ) : rejected ? (
        <Card style={{ borderColor: alpha(rejected.kind === "contrainte" ? colors.bad : colors.warn, 0.45) }}>
          <Row>
            <Icon name={rejected.kind === "contrainte" ? "ban" : "trendingDown"} size={20} color={rejected.kind === "contrainte" ? colors.bad : colors.warn} />
            <Text style={[type.h3, { flex: 1 }]}>{rejected.kind === "contrainte" ? t.fiche.ruledOut : t.fiche.lowerRanked}</Text>
          </Row>
          <Text style={type.body}>{rejected.reason}</Text>
          <Row>{(rejected.evidence_ids ?? []).map((id) => <EvidenceChip key={id} id={id} runId={runParam} />)}</Row>
        </Card>
      ) : (
        <Card>
          <Text style={type.body}>{t.fiche.notRetained}</Text>
        </Card>
      )}

      {/* 2. Graphe de dépendances */}
      <Section title={t.fiche.ecosystem}>
        {graph.isLoading ? <Loading /> : graph.error ? <ErrorState error={graph.error} /> : <SupplyChainGraph graph={graph.data!} runId={runParam} />}
        <Text style={type.caption}>{t.fiche.ecosystemNote}</Text>
      </Section>

      {/* 3. Risque */}
      <Section title={t.fiche.risk}>
        <Card style={{ paddingVertical: space.sm }}>
          {metrics.map((m) => <RiskMeter key={m.metric} m={m} runId={runParam} />)}
          {!advanced ? <Text style={[type.caption, { paddingVertical: space.sm }]}>{t.fiche.advancedHint}</Text> : null}
        </Card>
        {item && item.risks.length > 0 ? (
          <Card>
            <Row>
              <Icon name="alert" size={18} color={colors.warn} />
              <Text style={type.h3}>{t.fiche.vigilance}</Text>
            </Row>
            {item.risks.map((r) => <Text key={r} style={type.body}>• {r}</Text>)}
          </Card>
        ) : null}
      </Section>

      {/* 4. Débat */}
      {item ? (
        <Section title={t.fiche.debate}>
          <DebateSummary debate={item.debate} dissent={item.debate_summary.dissent} runId={runParam} />
        </Section>
      ) : null}

      {/* 5. Signaux */}
      <Section title={t.fiche.signals}>
        <Card style={{ gap: space.md }}>
          {a.signals.length === 0 ? (
            <Text style={type.body}>{t.fiche.noSignals}</Text>
          ) : (
            a.signals.map((c) => <ClaimLine key={c.text} claim={c} runId={runParam} />)
          )}
        </Card>
      </Section>

      {/* 6. Pourquoi ce classement */}
      {item ? (
        <Section title={t.fiche.ranking}>
          <Card>
            <ContributionBars contributions={item.contributions} weights={profile.data?.weights} />
          </Card>
        </Section>
      ) : null}

      {/* 7. Ce que nous ne savons pas */}
      <UnknownsBlock items={[...(item?.unknowns ?? []), ...(item?.limits ?? [t.fiche.defaultLimit])]} />

      {runParam ? (
        <Button label={t.common.runTrail} variant="secondary" icon="activity" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runParam } })} />
      ) : null}
    </Screen>
  );
}
