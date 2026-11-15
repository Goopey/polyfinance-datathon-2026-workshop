/**
 * Écran : Pourquoi ? (feuille modale de preuve) — énoncé, valeur, source, trois dates, traitement, limites,
 * étiquette Fait / Hypothèse / Scénario ; lien vers le parcours de l'analyse.
 * Paramètres : `id` (evidence_id), `run` (facultatif).
 */
import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import type { ReactNode } from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { getEvidence } from "../../src/api/assets";
import { ClaimTag } from "../../src/components/ClaimTag";
import { Icon } from "../../src/components/Icon";
import { Button, Card, ErrorState, Loading, Row, Screen, Tap } from "../../src/components/ui";
import { fmtDate, fmtValue } from "../../src/format";
import { useT } from "../../src/i18n";
import { useDisplayId, useTx } from "../../src/i18n/data";
import { useSettings } from "../../src/store/settings";
import { alpha, colors, space } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";

export default function Preuve() {
  const t = useT();
  const tx = useTx();
  const displayName = useDisplayId();
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
        <Text style={type.small}>{t.preuve.typeLabel[e.type] ?? e.type} · {displayName(e.subject)}</Text>
      </Row>
      <Text style={type.h2}>{tx(e.statement)}</Text>
      {e.value !== null ? (
        <Text style={styles.value}>
          {fmtValue(e.value, e.unit)}
          {e.currency && e.unit === "%" ? <Text style={type.small}>  {t.preuve.computedIn(e.currency)}</Text> : null}
        </Text>
      ) : null}

      <Card style={{ gap: 0, paddingVertical: space.sm }}>
        <Field label={t.preuve.source}>
          {e.source.url ? (
            <Tap onPress={() => Linking.openURL(e.source.url!)} accessibilityRole="link" scaleTo={0.97} style={styles.srcLink}>
              <Text style={[type.body, { color: colors.link, textDecorationLine: "underline" }]}>{tx(e.source.name)}</Text>
              <Icon name="arrowRight" size={14} color={colors.link} />
            </Tap>
          ) : (
            <Text style={type.body}>{tx(e.source.name)}</Text>
          )}
        </Field>
        {w.start || w.end ? (
          <Field label={t.preuve.period}>
            <Text style={type.body}>
              {t.preuve.fromTo(fmtDate(w.start), fmtDate(w.end))}
              {w.observations ? t.preuve.observations(w.observations) : ""}
            </Text>
          </Field>
        ) : null}
        <Field label={t.preuve.dates}>
          <Text style={type.body}>{t.preuve.observed} {fmtDate(e.observed_at)}</Text>
          <Text style={type.body}>{t.preuve.published} {fmtDate(e.published_at)}</Text>
          <Text style={type.body}>{t.preuve.retrieved} {fmtDate(e.retrieved_at)}</Text>
        </Field>
        <Field label={t.preuve.processing}>
          <Text style={type.body}>{tx(e.processing)}</Text>
        </Field>
        {e.limits ? (
          <Field label={t.preuve.limits}>
            <Text style={type.body}>{tx(e.limits)}</Text>
          </Field>
        ) : null}
        {advanced ? (
          <Field label={t.preuve.producedBy} last>
            <Text style={type.small}>{e.produced_by} · {e.evidence_id}</Text>
          </Field>
        ) : null}
      </Card>

      {run ? (
        <Button label={t.common.runTrail} variant="secondary" icon="activity" onPress={() => router.push({ pathname: "/run/[id]", params: { id: run } })} />
      ) : null}
      <Button label={t.common.close} variant="ghost" onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))} />
    </Screen>
  );
}

function Field({ label, children, last }: { label: string; children: ReactNode; last?: boolean }) {
  return (
    <View style={[styles.field, last && { borderBottomWidth: 0 }]}>
      <Text style={type.eyebrow}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  value: { fontFamily, fontSize: 40, fontWeight: "800", color: colors.mint, letterSpacing: -1 },
  field: { gap: 4, paddingVertical: space.md, borderBottomWidth: 1, borderBottomColor: alpha(colors.mint, 0.07) },
  srcLink: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start" },
});
