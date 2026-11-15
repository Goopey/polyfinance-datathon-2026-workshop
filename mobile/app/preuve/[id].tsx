/**
 * Écran : Pourquoi ? (feuille modale de preuve) — énoncé, valeur, source, trois dates, traitement, limites,
 * étiquette Fait / Hypothèse / Scénario ; lien vers le parcours de l'analyse.
 * Paramètres : `id` (evidence_id), `run` (facultatif).
 */
import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { getEvidence } from "../../src/api/assets";
import { ClaimTag } from "../../src/components/ClaimTag";
import { Button, Card, ErrorState, Loading, Row, Screen } from "../../src/components/ui";
import { fmtDate, fmtValue } from "../../src/format";
import { useSettings } from "../../src/store/settings";
import { colors, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";

const TYPE_LABEL: Record<string, string> = {
  metric: "Indicateur calculé", filing: "Dépôt réglementaire", esg: "Document ESG", relation: "Relation du graphe",
  macro: "Donnée macroéconomique", news: "Nouvelle datée", profile: "Paramètre du profil",
};

export default function Preuve() {
  const { id, run } = useLocalSearchParams<{ id: string; run?: string }>();
  const advanced = useSettings((s) => s.mode === "avance");
  const q = useQuery({ queryKey: ["evidence", run ?? null, id], queryFn: () => getEvidence(id!, run), enabled: !!id });

  if (q.isLoading) return <Loading />;
  if (q.error) return <Screen><ErrorState error={q.error} onRetry={() => q.refetch()} /></Screen>;
  const e = q.data!;
  const w = e.window;

  return (
    <Screen>
      <Row>
        <ClaimTag kind={e.claim_kind} showFact />
        <Text style={type.small}>{TYPE_LABEL[e.type] ?? e.type} · {e.subject}</Text>
      </Row>
      <Text style={type.h2}>{e.statement}</Text>
      {e.value !== null ? (
        <Text style={styles.value}>
          {fmtValue(e.value, e.unit)}
          {e.currency && e.unit === "%" ? <Text style={type.small}>  (calculé en {e.currency})</Text> : null}
        </Text>
      ) : null}

      <Card>
        <Field label="Source">
          {e.source.url ? (
            <Pressable onPress={() => Linking.openURL(e.source.url!)} accessibilityRole="link">
              <Text style={[type.body, { color: colors.primary, textDecorationLine: "underline" }]}>{e.source.name}</Text>
            </Pressable>
          ) : (
            <Text style={type.body}>{e.source.name}</Text>
          )}
        </Field>
        {w.start || w.end ? (
          <Field label="Période décrite">
            <Text style={type.body}>
              Du {fmtDate(w.start)} au {fmtDate(w.end)}
              {w.observations ? ` · ${w.observations} observations` : ""}
            </Text>
          </Field>
        ) : null}
        <Field label="Dates">
          <Text style={type.body}>Observée : {fmtDate(e.observed_at)}</Text>
          <Text style={type.body}>Publiée : {fmtDate(e.published_at)}</Text>
          <Text style={type.body}>Extraite : {fmtDate(e.retrieved_at)}</Text>
        </Field>
        <Field label="Traitement">
          <Text style={type.body}>{e.processing}</Text>
        </Field>
        {e.limits ? (
          <Field label="Limites">
            <Text style={type.body}>{e.limits}</Text>
          </Field>
        ) : null}
        {advanced ? (
          <Field label="Produit par">
            <Text style={type.small}>{e.produced_by} · {e.evidence_id}</Text>
          </Field>
        ) : null}
      </Card>

      {run ? (
        <Button label="Parcours de l'analyse" variant="secondary" onPress={() => router.push({ pathname: "/run/[id]", params: { id: run } })} />
      ) : null}
      <Button label="Fermer" variant="ghost" onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))} />
    </Screen>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.field}>
      <Text style={type.label}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  value: { fontSize: 34, fontWeight: "700", color: colors.text },
  field: { gap: 2, paddingVertical: space.xs, borderBottomWidth: 1, borderBottomColor: colors.surfaceMuted },
});
