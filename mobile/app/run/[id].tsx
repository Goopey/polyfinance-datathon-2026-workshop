/**
 * Écran : Parcours de l'analyse — étapes exécutées dans l'ordre (statut, durée, modèle, outils)
 * et contrôles de gouvernance. On montre ce qui a été fait, pas ce que les modèles ont « pensé ».
 * Sur AWS, c'est l'historique d'exécution Step Functions (docs/05_EXPLICABILITE.md §3).
 */
import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { getTrace } from "../../src/api/runs";
import { EvidenceChip } from "../../src/components/EvidenceChip";
import { Icon, type IconName } from "../../src/components/Icon";
import { Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../../src/components/ui";
import { durationMs, fmtDate, fmtSeconds } from "../../src/format";
import { useT } from "../../src/i18n";
import { useDisplayId, useTx } from "../../src/i18n/data";
import { useSettings } from "../../src/store/settings";
import { alpha, colors, space } from "../../src/theme/tokens";
import { AGENT_COLOR } from "../../src/components/DebateSummary";
import { type } from "../../src/theme/typography";
import type { TraceStep } from "../../src/types/contracts";

const KIND_ICON: Record<TraceStep["kind"], IconName> = { code: "sliders", llm: "sparkles", controle: "check" };

export default function ParcoursAnalyse() {
  const t = useT();
  const tx = useTx();
  const displayName = useDisplayId();
  const advanced = useSettings((s) => s.mode === "avance");
  const { id } = useLocalSearchParams<{ id: string }>();
  const q = useQuery({ queryKey: ["trace", id], queryFn: () => getTrace(id!), enabled: !!id });
  if (q.isLoading) return <Loading />;
  if (q.error) return <Screen><ErrorState error={q.error} onRetry={() => q.refetch()} /></Screen>;
  const tr = q.data!;
  const controls = tr.steps.filter((s) => s.kind === "controle");

  return (
    <Screen>
      <Text style={type.caption}>
        {t.trail.header(displayName(tr.profile_id), fmtDate(tr.as_of))}{advanced ? ` · ${tr.run_id}` : ""}
      </Text>

      <Section title={t.trail.controls}>
        <Card style={{ gap: space.md }}>
          {controls.map((s) => {
            const ok = s.status === "ok";
            return (
              <View key={s.step} style={styles.control}>
                <View style={[styles.dot, { backgroundColor: ok ? colors.goodBg : colors.badBg }]}>
                  <Icon name={ok ? "check" : "x"} size={14} color={ok ? colors.good : colors.bad} strokeWidth={3} />
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={[type.label, !ok && { color: colors.bad }]}>{t.trail.steps[s.step] ?? s.step}</Text>
                  {s.note ? <Text style={type.small}>{tx(s.note)}</Text> : null}
                </View>
              </View>
            );
          })}
        </Card>
      </Section>

      <Section title={t.trail.stepsTitle}>
        {tr.steps.filter((s) => s.kind !== "controle").map((s) => <StepRow key={s.step} s={s} runId={tr.run_id} />)}
      </Section>
    </Screen>
  );
}

function StepRow({ s, runId }: { s: TraceStep; runId: string }) {
  const t = useT();
  const tx = useTx();
  const advanced = useSettings((st) => st.mode === "avance");
  const ms = durationMs(s.started_at, s.ended_at);
  const agent = /^debate\.(bull|realist|bear)\./.exec(s.step)?.[1] as keyof typeof AGENT_COLOR | undefined;
  const agentColor = agent ? AGENT_COLOR[agent] : undefined;
  const st = s.status === "ok"
    ? { icon: "check" as const, text: t.trail.done, fg: colors.good, bg: colors.goodBg }
    : s.status === "echec"
      ? { icon: "x" as const, text: t.trail.failed, fg: colors.bad, bg: colors.badBg }
      : { icon: "minus" as const, text: t.trail.na, fg: colors.neutral, bg: colors.neutralBg };
  return (
    <Card>
      <Row style={{ justifyContent: "space-between", flexWrap: "nowrap" }}>
        <Row style={{ flex: 1, flexWrap: "nowrap" }}>
          <View style={styles.kind}>
            <Icon name={KIND_ICON[s.kind]} size={16} color={agentColor ?? (s.kind === "llm" ? colors.hypothesis : colors.mint)} />
          </View>
          <Text style={[type.h3, { flex: 1 }, agentColor ? { color: agentColor } : null]}>{t.trail.steps[s.step] ?? s.step}</Text>
        </Row>
        <Pill icon={st.icon} text={st.text} fg={st.fg} bg={st.bg} />
      </Row>
      <Text style={type.small}>{t.trail.kind[s.kind]} · {fmtSeconds(ms)} s</Text>
      {s.model_id ? <Text style={type.small}>{t.trail.model(s.model_id, s.prompt_version)}</Text> : null}
      {s.version ? <Text style={type.small}>{t.trail.version(s.version)}</Text> : null}
      {s.tools_called && s.tools_called.length > 0 ? <Text style={type.small}>{t.trail.tools(s.tools_called.join(", "))}</Text> : null}
      {s.note ? <Text style={type.body}>{tx(s.note)}</Text> : null}
      {advanced && s.outputs && s.outputs.length > 0 ? (
        <Row>
          <Text style={type.small}>{t.trail.outputs}</Text>
          {s.outputs.map((o) => <EvidenceChip key={o} id={o} runId={runId} label={o} />)}
        </Row>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  control: { flexDirection: "row", alignItems: "flex-start", gap: space.md },
  dot: { width: 26, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  kind: {
    width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center",
    backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: alpha(colors.mint, 0.12),
  },
});
