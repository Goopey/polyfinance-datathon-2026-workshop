/**
 * Écran : Données — sources utilisées, dates d'extraction, limites, résultat des contrôles qualité,
 * et chronologie des preuves de l'analyse courante par date de publication (respect du point-in-time, S5).
 */
import { useQueries, useQuery } from "@tanstack/react-query";
import { StyleSheet, Text, View } from "react-native";
import { getDataOverview, getEvidence } from "../src/api/assets";
import { useRun } from "../src/api/runs";
import { ClaimTag } from "../src/components/ClaimTag";
import { EvidenceChip } from "../src/components/EvidenceChip";
import { Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../src/components/ui";
import { fmtDate } from "../src/format";
import { useProfileStore } from "../src/store/profile";
import { colors, space } from "../src/theme/tokens";
import { type } from "../src/theme/typography";
import type { Explanation } from "../src/types/contracts";

const STATUT: Record<string, { fg: string; bg: string; icon: string }> = {
  "utilisé": { fg: colors.good, bg: colors.goodBg, icon: "✓" },
  "prévu": { fg: colors.neutral, bg: colors.neutralBg, icon: "○" },
};
const CHECK = {
  ok: { icon: "✓", color: colors.good, label: "Aucune remarque" },
  avertissement: { icon: "!", color: colors.warn, label: "Avertissement" },
  erreur: { icon: "✕", color: colors.bad, label: "Erreur" },
} as const;

function evidenceIdsOf(r: Explanation): string[] {
  const ids = new Set<string>();
  for (const i of r.items) {
    i.why.forEach((c) => c.evidence_ids.forEach((x) => ids.add(x)));
    i.debate.forEach((d) => d.arguments.forEach((c) => c.evidence_ids.forEach((x) => ids.add(x))));
  }
  r.rejected.forEach((x) => x.evidence_ids?.forEach((id) => ids.add(id)));
  return [...ids];
}

export default function Donnees() {
  const overview = useQuery({ queryKey: ["data"], queryFn: getDataOverview });
  const { profileId, runs } = useProfileStore();
  const run = useRun(profileId ? runs[profileId] : null);
  const ids = run.data?.result ? evidenceIdsOf(run.data.result) : [];
  const evidences = useQueries({ queries: ids.map((id) => ({ queryKey: ["evidence", id], queryFn: () => getEvidence(id) })) });

  if (overview.isLoading) return <Loading />;
  if (overview.error) return <Screen><ErrorState error={overview.error} onRetry={() => overview.refetch()} /></Screen>;
  const d = overview.data!;
  const asOf = run.data?.as_of ?? d.as_of;
  const timeline = evidences.map((q) => q.data).filter((e) => !!e)
    .sort((a, b) => a!.published_at.localeCompare(b!.published_at));
  const future = timeline.filter((e) => e!.published_at > asOf);

  return (
    <Screen>
      <Text style={type.body}>
        Pour chaque donnée : d'où elle vient, quand elle a été extraite, comment elle est traitée et ses limites. Analyse au {fmtDate(asOf)}.
      </Text>

      <Section title="Sources">
        {d.sources.map((s) => {
          const st = STATUT[s.statut] ?? { fg: colors.textMuted, bg: colors.surfaceMuted, icon: "–" };
          return (
            <Card key={s.source_id}>
              <Row style={{ justifyContent: "space-between" }}>
                <Text style={[type.h3, { flex: 1 }]}>{s.nom}</Text>
                <Pill icon={st.icon} text={s.statut} fg={st.fg} bg={st.bg} />
              </Row>
              <Text style={type.small}>{s.type_de_donnee}{s.date_extraction ? ` · extrait le ${fmtDate(s.date_extraction)}` : ""}</Text>
              {s.limites !== "—" ? <Text style={type.body}>Limites : {s.limites}</Text> : null}
            </Card>
          );
        })}
      </Section>

      <Section title="Contrôles qualité">
        <Card>
          {d.quality.map((c) => {
            const k = CHECK[c.status];
            return (
              <View key={c.check} style={styles.check}>
                <Text style={[type.label, { color: k.color }]}>{k.icon} {c.check}</Text>
                <Text style={type.caption}>{k.label}</Text>
                {c.details.map((x) => <Text key={x} style={type.small}>{x}</Text>)}
              </View>
            );
          })}
        </Card>
      </Section>

      <Section title="Chronologie des preuves de l'analyse">
        {!run.data?.result ? (
          <Text style={type.body}>Aucune analyse terminée pour le profil courant.</Text>
        ) : (
          <Card>
            <Text style={[type.label, { color: future.length ? colors.bad : colors.good }]}>
              {future.length
                ? `✕ ${future.length} preuve(s) publiée(s) après la date d'analyse`
                : `✓ Aucune preuve publiée après le ${fmtDate(asOf)} (point-in-time)`}
            </Text>
            {timeline.map((e) => (
              <View key={e!.evidence_id} style={styles.event}>
                <Text style={[type.caption, { width: 92 }]}>{e!.published_at}</Text>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={type.small}>{e!.subject} — {e!.statement}</Text>
                  <Row>
                    <ClaimTag kind={e!.claim_kind} />
                    <EvidenceChip id={e!.evidence_id} runId={run.data!.run_id} />
                  </Row>
                </View>
              </View>
            ))}
          </Card>
        )}
      </Section>
    </Screen>
  );
}

const styles = StyleSheet.create({
  check: { gap: 2, paddingVertical: space.xs, borderBottomWidth: 1, borderBottomColor: colors.surfaceMuted },
  event: { flexDirection: "row", gap: space.sm, paddingVertical: space.xs, borderTopWidth: 1, borderTopColor: colors.surfaceMuted },
});
