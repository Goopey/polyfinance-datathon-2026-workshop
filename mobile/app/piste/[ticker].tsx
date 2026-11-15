/**
 * Écran : Fiche d'une piste — aperçu (score sur 100), pourquoi, cours observés, risque, débat, sentiment du marché,
 * écosystème (graphe de dépendances), actualités et événements, pourquoi ce classement, ce que nous ne savons pas.
 * Règle : une section n'apparaît que si l'API fournit des données pour cet actif (rien d'inventé, rien de vide).
 * Conception : docs/07_UX_UI.md §3. Paramètres : `ticker`, `run` (facultatif : l'analyse dont la piste est issue).
 */
import { useQuery } from "@tanstack/react-query";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { getAsset, getGraph, getPrices } from "../../src/api/assets";
import { getProfile } from "../../src/api/profiles";
import { useRun } from "../../src/api/runs";
import { ContributionBars } from "../../src/components/ContributionBars";
import { DebateSummary } from "../../src/components/DebateSummary";
import { ClaimLine, EvidenceChip } from "../../src/components/EvidenceChip";
import { ConfidenceBadge, FitBadge } from "../../src/components/FitBadge";
import { Icon } from "../../src/components/Icon";
import { PriceChart } from "../../src/components/PriceChart";
import { RiskMeter } from "../../src/components/RiskMeter";
import { ScoreRing } from "../../src/components/ScoreRing";
import { SentimentGauge } from "../../src/components/SentimentGauge";
import { SupplyChainGraph, hasGraph } from "../../src/components/SupplyChainGraph";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, Collapsible, ErrorState, FadeIn, Loading, Pill, Row, Screen, Section } from "../../src/components/ui";
import { fmtNum } from "../../src/format";
import { useT } from "../../src/i18n";
import { useTx } from "../../src/i18n/data";
import { useProfileStore } from "../../src/store/profile";
import { useSettings } from "../../src/store/settings";
import { alpha, colors, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import { CRITERIA } from "../../src/types/contracts";

const FIT_COLOR = { "élevée": colors.good, partielle: colors.warn, faible: colors.bad } as const;

export default function FichePiste() {
  const t = useT();
  const tx = useTx();
  const { ticker, run: runParam } = useLocalSearchParams<{ ticker: string; run?: string }>();
  const currentProfile = useProfileStore((s) => s.profileId);
  const advanced = useSettings((s) => s.mode === "avance");
  const run = useRun(runParam);
  const profileId = run.data?.profile_id ?? currentProfile ?? undefined;
  const sheet = useQuery({ queryKey: ["asset", ticker, profileId, runParam], queryFn: () => getAsset(ticker!, { profileId, runId: runParam }), enabled: !!ticker });
  const graph = useQuery({ queryKey: ["graph", ticker, runParam], queryFn: () => getGraph(ticker!, runParam), enabled: !!ticker });
  const prices = useQuery({ queryKey: ["prices", ticker, runParam], queryFn: () => getPrices(ticker!, runParam), enabled: !!ticker, retry: false });
  const profile = useQuery({ queryKey: ["profile", profileId], queryFn: () => getProfile(profileId!), enabled: !!profileId });

  if (sheet.isLoading || (runParam && run.isLoading)) return <Loading />;
  if (sheet.error) return <Screen><ErrorState error={sheet.error} onRetry={() => sheet.refetch()} /></Screen>;
  const a = sheet.data!;
  const result = run.data?.result ?? null;
  const item = result?.items.find((i) => i.ticker === ticker) ?? null;
  const rejected = result?.rejected.find((r) => r.ticker === ticker) ?? null;
  const metrics = a.metrics.filter((m) => advanced || !m.advanced);
  const score = item ? CRITERIA.reduce((s, k) => s + (item.contributions[k] ?? 0), 0) * 100 : null;
  const unknowns = [...(item?.unknowns ?? []), ...(item?.limits ?? [])];

  return (
    <Screen>
      <Stack.Screen options={{ title: a.name }} />

      {/* 1. Aperçu */}
      <FadeIn>
        <View style={styles.hero}>
          <View style={{ flex: 1, gap: space.xs }}>
            <Text style={type.eyebrow}>
              {a.ticker} · {t.assetClass[a.asset_class] ?? a.asset_class}
            </Text>
            <Text style={type.display}>{a.name}</Text>
            <Text style={type.small}>
              {a.sector ? `${tx(a.sector)} · ` : ""}{t.fiche.listed(a.currency)}
            </Text>
          </View>
          {item && score !== null ? (
            <ScoreRing score={score} size={84} color={FIT_COLOR[item.fit]} label={t.contributions.scoreValue(fmtNum(score, 0))} />
          ) : null}
        </View>
        {item ? (
          <Row style={{ marginTop: space.md }}>
            <FitBadge fit={item.fit} />
            <ConfidenceBadge confidence={item.confidence} />
            {item.to_review ? <Pill icon="alert" text={t.pistes.toReview} fg={colors.bad} bg={colors.badBg} /> : null}
          </Row>
        ) : null}
      </FadeIn>

      {item && item.why.length > 0 ? (
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
          <Text style={type.body}>{tx(rejected.reason)}</Text>
          <Row>{(rejected.evidence_ids ?? []).map((id) => <EvidenceChip key={id} id={id} runId={runParam} />)}</Row>
        </Card>
      ) : null}

      {/* 2. Cours observés */}
      {prices.data && prices.data.points.length > 1 ? (
        <Section title={t.fiche.prices}>
          <Card>
            <PriceChart series={prices.data} runId={runParam} />
          </Card>
        </Section>
      ) : null}

      {/* 3. Risque */}
      {metrics.length > 0 ? (
        <Section title={t.fiche.risk}>
          <Card style={{ paddingVertical: space.sm }}>
            {metrics.map((m) => <RiskMeter key={m.metric} m={m} runId={runParam} />)}
          </Card>
          {item && item.risks.length > 0 ? (
            <Card>
              <Row>
                <Icon name="alert" size={18} color={colors.warn} />
                <Text style={type.h3}>{t.fiche.vigilance}</Text>
              </Row>
              {item.risks.map((r) => <Text key={r} style={type.body}>• {tx(r)}</Text>)}
            </Card>
          ) : null}
        </Section>
      ) : null}

      {/* 4. Débat */}
      {item && item.debate.length > 0 ? (
        <Section title={t.fiche.debate}>
          <DebateSummary debate={item.debate} dissent={item.debate_summary.dissent} runId={runParam} />
        </Section>
      ) : null}

      {/* 5. Sentiment du marché (affichage seulement ; actions seulement) */}
      {a.sentiment ? (
        <Section title={t.fiche.sentiment}>
          <Card>
            <SentimentGauge sentiment={a.sentiment} runId={runParam} />
          </Card>
        </Section>
      ) : null}

      {/* 6. Écosystème : graphe de dépendances (seulement si des liens sourcés existent) */}
      {hasGraph(graph.data) ? (
        <Section title={t.fiche.ecosystem}>
          <SupplyChainGraph graph={graph.data!} runId={runParam} />
        </Section>
      ) : null}

      {/* 7. Actualités et événements datés (ESG, nouvelles, dépôts) fournis par l'agent de recherche */}
      {a.signals.length > 0 ? (
        <Section title={t.fiche.signals}>
          <Card style={{ gap: space.md }}>
            {a.signals.map((c) => <ClaimLine key={c.text} claim={c} runId={runParam} />)}
          </Card>
        </Section>
      ) : null}

      {/* 8. Pourquoi ce classement */}
      {item ? (
        <Collapsible title={t.fiche.ranking} summary={t.fiche.rankingSummary(fmtNum(score ?? 0, 0))} icon="sliders">
          <ContributionBars contributions={item.contributions} weights={profile.data?.weights} notApplicable={item.not_applicable} />
        </Collapsible>
      ) : null}

      {/* 9. Ce que nous ne savons pas */}
      <UnknownsBlock items={unknowns} />

      {runParam ? (
        <Button label={t.common.runTrail} variant="ghost" icon="activity" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runParam } })} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { flexDirection: "row", alignItems: "center", gap: space.md },
});
