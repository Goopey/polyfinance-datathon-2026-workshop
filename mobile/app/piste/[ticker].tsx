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
import { RiskMeter } from "../../src/components/RiskMeter";
import { SupplyChainGraph } from "../../src/components/SupplyChainGraph";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../../src/components/ui";
import { fr } from "../../src/i18n/fr";
import { useProfileStore } from "../../src/store/profile";
import { useSettings } from "../../src/store/settings";
import { colors, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";

export default function FichePiste() {
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
        <Text style={type.title}>{a.name}</Text>
        <Text style={type.small}>
          {a.ticker} · {fr.assetClass[a.asset_class] ?? a.asset_class}
          {a.sector ? ` · ${a.sector}` : ""} · cotation en {a.currency}
        </Text>
        {item ? (
          <Row>
            <FitBadge fit={item.fit} />
            <ConfidenceBadge confidence={item.confidence} />
            {item.to_review ? <Pill icon="!" text="À examiner" fg={colors.bad} bg={colors.badBg} /> : null}
          </Row>
        ) : null}
      </View>
      {item ? (
        <Card>
          <Text style={type.h3}>Pourquoi cette piste</Text>
          {item.why.map((c) => <ClaimLine key={c.text} claim={c} runId={runParam} />)}
        </Card>
      ) : rejected ? (
        <Card style={{ borderColor: colors.warn }}>
          <Text style={type.h3}>{rejected.kind === "contrainte" ? "⛔ Écartée par une règle de votre profil" : "↓ Moins bien classée"}</Text>
          <Text style={type.body}>{rejected.reason}</Text>
          <Row>{(rejected.evidence_ids ?? []).map((id) => <EvidenceChip key={id} id={id} runId={runParam} />)}</Row>
        </Card>
      ) : (
        <Card>
          <Text style={type.body}>
            Ce titre n'est pas une piste retenue de cette analyse : pas de débat ni de score pour ce profil. Les indicateurs et le
            graphe restent consultables.
          </Text>
        </Card>
      )}

      {/* 2. Graphe de dépendances */}
      <Section title="Écosystème de la société">
        {graph.isLoading ? <Loading /> : graph.error ? <ErrorState error={graph.error} /> : <SupplyChainGraph graph={graph.data!} runId={runParam} />}
        <Text style={type.caption}>
          Deux pistes qui dépendent du même fournisseur se diversifient moins qu'il n'y paraît : le graphe alimente le critère « diversification ».
        </Text>
      </Section>

      {/* 3. Risque */}
      <Section title="Risque observé">
        <Card>
          {metrics.map((m) => <RiskMeter key={m.metric} m={m} runId={runParam} />)}
          {!advanced ? <Text style={type.caption}>Mode Avancé (onglet Profil) : rendement observé et détails.</Text> : null}
        </Card>
        {item && item.risks.length > 0 ? (
          <Card>
            <Text style={type.h3}>Points de vigilance</Text>
            {item.risks.map((r) => <Text key={r} style={type.body}>• {r}</Text>)}
          </Card>
        ) : null}
      </Section>

      {/* 4. Débat */}
      {item ? (
        <Section title="Débat Bull / Réaliste / Bear">
          <DebateSummary debate={item.debate} dissent={item.debate_summary.dissent} runId={runParam} />
        </Section>
      ) : null}

      {/* 5. Signaux */}
      <Section title="Signaux datés">
        <Card>
          {a.signals.length === 0 ? (
            <Text style={type.body}>Aucun signal ESG ni nouvelle datée pour cet actif. C'est une information manquante, pas un bon score.</Text>
          ) : (
            a.signals.map((c) => <ClaimLine key={c.text} claim={c} runId={runParam} />)
          )}
        </Card>
      </Section>

      {/* 6. Pourquoi ce classement */}
      {item ? (
        <Section title="Pourquoi ce classement">
          <Card>
            <ContributionBars contributions={item.contributions} weights={profile.data?.weights} />
          </Card>
        </Section>
      ) : null}

      {/* 7. Ce que nous ne savons pas */}
      <UnknownsBlock items={[...(item?.unknowns ?? []), ...(item?.limits ?? ["Fenêtre de 5 ans ; biais du survivant de l'univers."])]} />

      {runParam ? (
        <Button label="Parcours de l'analyse" variant="secondary" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runParam } })} />
      ) : null}
      <Text style={[type.caption, { textAlign: "center" }]}>Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier.</Text>
    </Screen>
  );
}
