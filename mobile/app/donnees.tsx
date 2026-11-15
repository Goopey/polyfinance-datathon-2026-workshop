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
import { Icon, type IconName } from "../src/components/Icon";
import { Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../src/components/ui";
import { fmtDate } from "../src/format";
import { useT } from "../src/i18n";
import { useProfileStore } from "../src/store/profile";
import { alpha, colors, space } from "../src/theme/tokens";
import { type } from "../src/theme/typography";
import type { Explanation } from "../src/types/contracts";

const STATUT: Record<string, { fg: string; bg: string; icon: IconName }> = {
  "utilisé": { fg: colors.good, bg: colors.goodBg, icon: "check" },
  "prévu": { fg: colors.neutral, bg: colors.neutralBg, icon: "minus" },
};
const CHECK = {
  ok: { icon: "check", color: colors.good },
  avertissement: { icon: "alert", color: colors.warn },
  erreur: { icon: "x", color: colors.bad },
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
  const t = useT();
  const { profileId, runs } = useProfileStore();
  const runId = profileId ? runs[profileId] : null;
  const overview = useQuery({ queryKey: ["data", runId], queryFn: () => getDataOverview(runId) });
  const run = useRun(runId);
  const ids = run.data?.result ? evidenceIdsOf(run.data.result) : [];
  const evidences = useQueries({ queries: ids.map((id) => ({ queryKey: ["evidence", runId, id], queryFn: () => getEvidence(id, runId) })) });

  if (overview.isLoading) return <Loading />;
  if (overview.error) return <Screen><ErrorState error={overview.error} onRetry={() => overview.refetch()} /></Screen>;
  const d = overview.data!;
  const asOf = run.data?.as_of ?? d.as_of;
  const timeline = evidences.map((q) => q.data).filter((e) => !!e)
    .sort((a, b) => a!.published_at.localeCompare(b!.published_at));
  const future = timeline.filter((e) => e!.published_at > asOf);

  return (
    <Screen>
      <Text style={[type.body, { color: colors.textMuted }]}>{t.donnees.intro(fmtDate(asOf))}</Text>

      <Section title={t.donnees.sources}>
        {d.sources.map((s) => {
          const st = STATUT[s.statut] ?? { fg: colors.textMuted, bg: colors.neutralBg, icon: "minus" as IconName };
          return (
            <Card key={s.source_id}>
              <Row style={{ justifyContent: "space-between", flexWrap: "nowrap" }}>
                <Text style={[type.h3, { flex: 1 }]}>{s.nom}</Text>
                <Pill icon={st.icon} text={t.donnees.statut[s.statut] ?? s.statut} fg={st.fg} bg={st.bg} />
              </Row>
              <Text style={type.small}>{s.type_de_donnee}{s.date_extraction ? t.donnees.extracted(fmtDate(s.date_extraction)) : ""}</Text>
              {s.limites !== "—" ? <Text style={type.body}>{t.donnees.limits(s.limites)}</Text> : null}
            </Card>
          );
        })}
      </Section>

      <Section title={t.donnees.quality}>
        <Card style={{ gap: 0, paddingVertical: space.sm }}>
          {d.quality.map((c, i) => {
            const k = CHECK[c.status];
            return (
              <View key={c.check} style={[styles.check, i === d.quality.length - 1 && { borderBottomWidth: 0 }]}>
                <Row style={{ flexWrap: "nowrap" }}>
                  <Icon name={k.icon} size={16} color={k.color} strokeWidth={2.6} />
                  <Text style={[type.label, { color: k.color, flex: 1 }]}>{c.check}</Text>
                </Row>
                <Text style={type.caption}>{t.donnees.check[c.status]}</Text>
                {c.details.map((x) => <Text key={x} style={type.small}>{x}</Text>)}
              </View>
            );
          })}
        </Card>
      </Section>

      <Section title={t.donnees.timeline}>
        {!run.data?.result ? (
          <Text style={type.body}>{t.donnees.noRun}</Text>
        ) : (
          <Card>
            <Row style={{ flexWrap: "nowrap" }}>
              <Icon name={future.length ? "x" : "check"} size={18} color={future.length ? colors.bad : colors.good} strokeWidth={2.6} />
              <Text style={[type.label, { flex: 1, color: future.length ? colors.bad : colors.good }]}>
                {future.length ? t.donnees.future(future.length) : t.donnees.clean(fmtDate(asOf))}
              </Text>
            </Row>
            {timeline.map((e) => (
              <View key={e!.evidence_id} style={styles.event}>
                <View style={styles.rail}>
                  <View style={styles.railDot} />
                </View>
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={[type.caption, { color: colors.mint }]}>{e!.published_at}</Text>
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
  check: { gap: 2, paddingVertical: space.md, borderBottomWidth: 1, borderBottomColor: alpha(colors.mint, 0.07) },
  event: { flexDirection: "row", gap: space.md, paddingVertical: space.sm },
  rail: { width: 12, alignItems: "center", paddingTop: 4 },
  railDot: { width: 9, height: 9, borderRadius: 5, backgroundColor: colors.primary, borderWidth: 2, borderColor: alpha(colors.mint, 0.4) },
});
