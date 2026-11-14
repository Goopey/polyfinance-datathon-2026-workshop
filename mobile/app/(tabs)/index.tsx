/**
 * Écran : Pistes à explorer (accueil) — rappel du profil, progression de l'analyse, cartes,
 * « Écartées et pourquoi », état « Aucune recommandation », bouton flottant « Tester une idée ».
 */
import { Redirect, router } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { EvidenceChip } from "../../src/components/EvidenceChip";
import { MoveCard } from "../../src/components/MoveCard";
import { RunProgress } from "../../src/components/RunProgress";
import { UnknownsBlock } from "../../src/components/UnknownsBlock";
import { Button, Card, ErrorState, Loading, Row, Screen, Section } from "../../src/components/ui";
import { fmtDate } from "../../src/format";
import { useBaseRun } from "../../src/hooks/useBaseRun";
import { fr } from "../../src/i18n/fr";
import { useProfileStore } from "../../src/store/profile";
import { colors, radius, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import type { Explanation, RejectedItem } from "../../src/types/contracts";

export default function Pistes() {
  const { profileId, summary } = useProfileStore();
  const { runId, query, startError, restart } = useBaseRun(profileId);
  if (!profileId) return <Redirect href="/onboarding" />;
  const run = query.data;
  const result = run?.result ?? null;

  return (
    <View style={{ flex: 1 }}>
      <Screen>
        <Card style={styles.profileLine}>
          <Text style={type.label}>{summary}</Text>
          <Row style={{ justifyContent: "space-between" }}>
            <Text style={type.small}>Données au {fmtDate(run?.as_of ?? null)}</Text>
            <Pressable onPress={() => router.push("/(tabs)/profil")} hitSlop={10} accessibilityRole="link">
              <Text style={styles.link}>Changer de profil</Text>
            </Pressable>
          </Row>
        </Card>

        {startError ? (
          <ErrorState error={startError} onRetry={restart} />
        ) : query.error ? (
          <ErrorState error={query.error} onRetry={restart} />
        ) : !run ? (
          <Loading label="Lancement de l'analyse…" />
        ) : run.status === "en_cours" ? (
          <RunProgress steps={run.steps} />
        ) : run.status === "echec" ? (
          <ErrorState error={run.error ?? "L'analyse a échoué."} onRetry={restart} />
        ) : result ? (
          <Results result={result} runId={runId!} />
        ) : null}

        {result ? (
          <View style={{ gap: space.sm }}>
            <Button label="Parcours de l'analyse" variant="secondary" onPress={() => router.push({ pathname: "/run/[id]", params: { id: runId! } })} />
            <Button label="Comparer deux profils" variant="secondary" onPress={() => router.push("/comparer")} />
            <Button label="Données et sources" variant="secondary" onPress={() => router.push("/donnees")} />
            <Button label="Relancer l'analyse" variant="ghost" onPress={restart} />
            <Text style={[type.caption, { textAlign: "center" }]}>{result.disclaimer}</Text>
          </View>
        ) : null}
      </Screen>

      <Pressable
        onPress={() => router.push("/(tabs)/tester")}
        accessibilityRole="button"
        accessibilityLabel="Tester une idée"
        style={({ pressed }) => [styles.fab, pressed && { opacity: 0.85 }]}
      >
        <Text style={styles.fabText}>? Tester une idée</Text>
      </Pressable>
    </View>
  );
}

function Results({ result, runId }: { result: Explanation; runId: string }) {
  if (result.no_recommendation) return <NoRecommendation result={result} runId={runId} />;
  return (
    <>
      <Text style={type.title} accessibilityRole="header">{result.headline}</Text>
      <Text style={type.small}>Classées selon leur adéquation à votre profil. Touchez une piste pour comprendre pourquoi.</Text>
      {result.items.map((item, i) => (
        <MoveCard key={item.ticker} item={item} rank={i + 1} runId={runId} />
      ))}
      <RejectedList rejected={result.rejected} runId={runId} />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function NoRecommendation({ result, runId }: { result: Explanation; runId: string }) {
  return (
    <>
      <Card style={{ borderColor: colors.warn, borderWidth: 1.5 }}>
        <Text style={type.title} accessibilityRole="header">∅ {fr.noRecoTitle}</Text>
        <Text style={type.body}>{fr.noRecoBody}</Text>
        {result.missing.map((m) => (
          <Text key={m} style={type.body}>• {m}</Text>
        ))}
        <Text style={type.small}>C'est une réponse valide : le système sait dire « je ne sais pas ».</Text>
        <Button label="Revoir les règles du profil" variant="secondary" onPress={() => router.push("/(tabs)/profil")} />
      </Card>
      <RejectedList rejected={result.rejected} runId={runId} initiallyOpen />
      <UnknownsBlock items={result.unknowns} />
    </>
  );
}

function RejectedList({ rejected, runId, initiallyOpen = false }: { rejected: RejectedItem[]; runId: string; initiallyOpen?: boolean }) {
  const [open, setOpen] = useState(initiallyOpen);
  if (rejected.length === 0) return null;
  const rules = rejected.filter((r) => r.kind === "contrainte");
  const ranked = rejected.filter((r) => r.kind !== "contrainte");
  return (
    <Section
      title={`${fr.rejectedTitle} (${rejected.length})`}
      right={
        <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }} hitSlop={10}>
          <Text style={styles.link}>{open ? "Replier ▲" : "Déplier ▼"}</Text>
        </Pressable>
      }
    >
      {open ? (
        <View style={{ gap: space.md }}>
          {rules.length > 0 ? <RejectedGroup title="Écartées par une règle de votre profil" items={rules} runId={runId} icon="⛔" /> : null}
          {ranked.length > 0 ? <RejectedGroup title="Moins bien classées ou déclassées" items={ranked} runId={runId} icon="↓" /> : null}
        </View>
      ) : null}
    </Section>
  );
}

function RejectedGroup({ title, items, runId, icon }: { title: string; items: RejectedItem[]; runId: string; icon: string }) {
  return (
    <Card>
      <Text style={type.h3}>{title}</Text>
      {items.map((r) => (
        <View key={r.ticker} style={styles.rejRow}>
          <Text style={type.label}>{icon} {r.ticker}</Text>
          <Text style={type.body}>{r.reason}</Text>
          <Row>
            {(r.evidence_ids ?? []).map((id) => <EvidenceChip key={id} id={id} runId={runId} />)}
            <Pressable onPress={() => router.push({ pathname: "/piste/[ticker]", params: { ticker: r.ticker, run: runId } })} hitSlop={8}>
              <Text style={styles.link}>Voir la fiche →</Text>
            </Pressable>
          </Row>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  profileLine: { backgroundColor: colors.surfaceMuted, gap: space.xs },
  link: { color: colors.primary, fontWeight: "600", fontSize: 15 },
  rejRow: { gap: space.xs, paddingVertical: space.sm, borderTopWidth: 1, borderTopColor: colors.surfaceMuted },
  fab: {
    position: "absolute", right: space.lg, bottom: space.lg, backgroundColor: colors.primary,
    borderRadius: radius.pill, paddingHorizontal: space.xl, paddingVertical: space.md, minHeight: 52, justifyContent: "center",
    shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 5,
  },
  fabText: { color: colors.primaryText, fontWeight: "700", fontSize: 16 },
});
