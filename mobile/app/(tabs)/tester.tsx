/**
 * Écran : Tester une idée — l'utilisateur choisit un titre ; le système dit s'il est cohérent avec le profil
 * et pourquoi : verdict, tensions chiffrées, effet sur le panier simulé, alternatives étayées (test Robert).
 * Le titre demandé est toujours analysé, jamais filtré en silence.
 */
import { useQuery } from "@tanstack/react-query";
import { Redirect, router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { listAssets } from "../../src/api/assets";
import { startRun, useRun } from "../../src/api/runs";
import { ClaimLine } from "../../src/components/EvidenceChip";
import { RunProgress } from "../../src/components/RunProgress";
import { Button, Card, ErrorState, Loading, Screen, Section } from "../../src/components/ui";
import { fr } from "../../src/i18n/fr";
import { useProfileStore } from "../../src/store/profile";
import { colors, radius, space, touchMin } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import type { CoherenceAnalysis, Verdict } from "../../src/types/contracts";

const VERDICT: Record<Verdict, { icon: string; fg: string; bg: string }> = {
  "cohérent": { icon: "✓", fg: colors.good, bg: colors.goodBg },
  "cohérent avec réserve": { icon: "◆", fg: colors.warn, bg: colors.warnBg },
  "incohérent avec le profil": { icon: "✕", fg: colors.bad, bg: colors.badBg },
};

export default function TesterIdee() {
  const { profileId, label } = useProfileStore();
  const [search, setSearch] = useState("");
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
          <Text style={type.title} accessibilityRole="header">Un titre vous fait envie ?</Text>
          <Text style={type.body}>
            Choisissez-le : nous vérifions s'il est cohérent avec le profil {label ? `« ${label} »` : ""}, chiffres et sources à l'appui.
          </Text>
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="Rechercher un nom ou un symbole"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            accessibilityLabel="Rechercher un titre"
            autoCapitalize="characters"
          />
          {startError ? <ErrorState error={startError} /> : null}
          {assets.isLoading ? <Loading /> : assets.error ? <ErrorState error={assets.error} onRetry={() => assets.refetch()} /> : null}
          <View style={{ gap: space.sm }}>
            {filtered.map((a) => (
              <Pressable key={a.ticker} onPress={() => test(a.ticker)} accessibilityRole="button" accessibilityLabel={`Tester ${a.name}`}
                style={({ pressed }) => [styles.assetRow, pressed && { opacity: 0.8 }]}>
                <View style={{ flex: 1 }}>
                  <Text style={type.h3}>{a.name}</Text>
                  <Text style={type.small}>{a.ticker} · {fr.assetClass[a.asset_class] ?? a.asset_class}{a.sector ? ` · ${a.sector}` : ""}</Text>
                </View>
                <Text style={styles.chevron}>›</Text>
              </Pressable>
            ))}
            {assets.data && filtered.length === 0 ? <Text style={type.body}>Aucun titre de l'univers ne correspond.</Text> : null}
          </View>
        </>
      ) : run.error ? (
        <ErrorState error={run.error} onRetry={reset} />
      ) : !status || status.status === "en_cours" ? (
        status ? <RunProgress steps={status.steps} /> : <Loading label="Lancement de l'analyse…" />
      ) : coherence ? (
        <CoherenceView c={coherence} runId={runId} />
      ) : (
        <ErrorState error={status.error ?? "Analyse de cohérence absente du résultat."} onRetry={reset} />
      )}

      {runId && status?.status !== "en_cours" ? <Button label="Tester un autre titre" variant="secondary" onPress={reset} /> : null}
    </Screen>
  );
}

function CoherenceView({ c, runId }: { c: CoherenceAnalysis; runId: string }) {
  const v = VERDICT[c.verdict];
  return (
    <>
      <Text style={type.small}>Analyse de cohérence</Text>
      <Text style={type.title}>{c.name}</Text>
      <View style={[styles.verdict, { backgroundColor: v.bg, borderColor: v.fg }]} accessibilityRole="summary">
        <Text style={[styles.verdictText, { color: v.fg }]}>{v.icon} {fr.verdict[c.verdict]}</Text>
        <Text style={type.small}>
          Ce verdict n'est ni une approbation ni un refus : c'est une mise en contexte de l'idée par rapport aux règles et aux poids du profil.
        </Text>
      </View>

      <Section title={`Tensions avec le profil (${c.tensions.length})`}>
        <Card>
          {c.tensions.length === 0 ? (
            <Text style={type.body}>Aucune tension relevée entre ce titre et le profil.</Text>
          ) : (
            c.tensions.map((t) => <ClaimLine key={t.text} claim={t} runId={runId} />)
          )}
        </Card>
      </Section>

      {c.context.length > 0 ? (
        <Section title="Effet sur le panier simulé">
          <Card style={{ backgroundColor: colors.scenarioBg, borderColor: colors.scenarioBg }}>
            {c.context.map((t) => <ClaimLine key={t.text} claim={t} runId={runId} />)}
          </Card>
        </Section>
      ) : null}

      {c.alternatives.length > 0 ? (
        <Section title="Pistes qui répondent avec moins de tension">
          {c.alternatives.map((alt) => (
            <Card key={alt.ticker}>
              <Text style={type.h3}>{alt.name}</Text>
              <ClaimLine claim={alt.why} runId={runId} />
              <Button label="Voir la fiche" variant="ghost"
                onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: alt.ticker, run: runId } })} />
            </Card>
          ))}
        </Section>
      ) : null}

      <Button label={`Voir la fiche de ${c.name}`} variant="secondary"
        onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: c.ticker, run: runId } })} />
      <Button label="Parcours de l'analyse" variant="ghost" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runId } })} />
    </>
  );
}

const styles = StyleSheet.create({
  input: {
    minHeight: touchMin + 4, borderWidth: 1.5, borderColor: colors.border, borderRadius: radius.md,
    paddingHorizontal: space.md, fontSize: 16, backgroundColor: colors.surface, color: colors.text,
  },
  assetRow: {
    flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border, padding: space.md, minHeight: touchMin + 12,
  },
  chevron: { fontSize: 26, color: colors.textMuted },
  verdict: { borderWidth: 2, borderRadius: radius.lg, padding: space.lg, gap: space.sm },
  verdictText: { fontSize: 22, fontWeight: "700" },
});
