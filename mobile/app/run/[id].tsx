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
import { Card, ErrorState, Loading, Pill, Row, Screen, Section } from "../../src/components/ui";
import { durationMs, fmtDate } from "../../src/format";
import { useSettings } from "../../src/store/settings";
import { colors, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import type { TraceStep } from "../../src/types/contracts";

const KIND = {
  code: { icon: "⚙", label: "Code déterministe" },
  llm: { icon: "✎", label: "Agent (modèle de langage)" },
  controle: { icon: "⛨", label: "Contrôle de gouvernance" },
} as const;

const STEP_LABEL: Record<string, string> = {
  profil: "Pondération du profil",
  recherche: "Recherche",
  validation: "Validation financière",
  dossiers_de_preuves: "Dossiers de preuves et contraintes du profil",
  "controle.avant_debat": "Contrôle avant le débat",
  "debate.bull.round1": "Débat, tour 1 — Bull",
  "debate.realist.round1": "Débat, tour 1 — Réaliste",
  "debate.bear.round1": "Débat, tour 1 — Bear",
  "debate.bull.round3": "Débat, position finale — Bull",
  "debate.realist.round3": "Débat, position finale — Réaliste",
  "debate.bear.round3": "Débat, position finale — Bear",
  debat: "Débat",
  decision: "Moteur de décision",
  "controle.plafonds_panier": "Contrôle des plafonds du panier simulé",
  "controle.diversification": "Contrôle de diversification",
  "controle.aucune_recommandation": "Contrôle « aucune recommandation »",
  explication: "Explication",
  "controle.avant_affichage": "Contrôle avant l'affichage",
};

export default function ParcoursAnalyse() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const q = useQuery({ queryKey: ["trace", id], queryFn: () => getTrace(id!), enabled: !!id });
  if (q.isLoading) return <Loading />;
  if (q.error) return <Screen><ErrorState error={q.error} onRetry={() => q.refetch()} /></Screen>;
  const t = q.data!;
  const controls = t.steps.filter((s) => s.kind === "controle");

  return (
    <Screen>
      <Text style={type.small}>Analyse {t.run_id} · profil {t.profile_id} · données au {fmtDate(t.as_of)}</Text>
      <Text style={type.body}>
        Les étapes réellement exécutées, dans l'ordre. Les chiffres viennent des étapes ⚙ (code) ; les agents ✎ argumentent et rédigent à partir
        des preuves, sans produire de chiffre.
      </Text>

      <Section title="Contrôles de gouvernance">
        <Card>
          {controls.map((s) => (
            <View key={s.step} style={styles.control}>
              <Text style={[type.label, s.status === "echec" && { color: colors.bad }]}>
                {s.status === "ok" ? "✓" : "✕"} {STEP_LABEL[s.step] ?? s.step}
              </Text>
              {s.note ? <Text style={type.body}>{s.note}</Text> : null}
            </View>
          ))}
        </Card>
      </Section>

      <Section title="Étapes">
        {t.steps.filter((s) => s.kind !== "controle").map((s) => <StepRow key={s.step} s={s} runId={t.run_id} />)}
      </Section>
    </Screen>
  );
}

function StepRow({ s, runId }: { s: TraceStep; runId: string }) {
  const advanced = useSettings((st) => st.mode === "avance");
  const k = KIND[s.kind];
  const ms = durationMs(s.started_at, s.ended_at);
  return (
    <Card>
      <Row style={{ justifyContent: "space-between" }}>
        <Text style={type.h3}>{k.icon} {STEP_LABEL[s.step] ?? s.step}</Text>
        <Pill
          icon={s.status === "ok" ? "✓" : s.status === "echec" ? "✕" : "–"}
          text={s.status === "ok" ? "Terminé" : s.status === "echec" ? "Échec" : "Sans objet"}
          fg={s.status === "ok" ? colors.good : s.status === "echec" ? colors.bad : colors.neutral}
          bg={s.status === "ok" ? colors.goodBg : s.status === "echec" ? colors.badBg : colors.neutralBg}
        />
      </Row>
      <Text style={type.small}>{k.label} · {(ms / 1000).toLocaleString("fr-CA", { maximumFractionDigits: 1 })} s</Text>
      {s.model_id ? <Text style={type.small}>Modèle : {s.model_id}{s.prompt_version ? ` · prompt ${s.prompt_version}` : ""}</Text> : null}
      {s.version ? <Text style={type.small}>Version : {s.version}</Text> : null}
      {s.tools_called && s.tools_called.length > 0 ? <Text style={type.small}>Outils appelés : {s.tools_called.join(", ")}</Text> : null}
      {s.note ? <Text style={type.body}>{s.note}</Text> : null}
      {advanced && s.outputs && s.outputs.length > 0 ? (
        <Row>
          <Text style={type.small}>Preuves produites :</Text>
          {s.outputs.map((o) => <EvidenceChip key={o} id={o} runId={runId} label={o} />)}
        </Row>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  control: { gap: 2, paddingVertical: space.xs },
});
