/**
 * Écran : Comparer deux profils côte à côte sur le même univers et la même date :
 * classements, règles appliquées, différences surlignées (scénario S12 ; extra n° 2, utile pour la vidéo).
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { getPersonas, getProfile } from "../src/api/profiles";
import { RunProgress } from "../src/components/RunProgress";
import { Card, ErrorState, Loading, Row, Screen, Section, Tap } from "../src/components/ui";
import { fmtWeight } from "../src/format";
import { useBaseRun } from "../src/hooks/useBaseRun";
import { useT } from "../src/i18n";
import { alpha, colors, radius, space, touchMin } from "../src/theme/tokens";
import { fontFamily, type } from "../src/theme/typography";
import { CRITERIA, type Explanation, type ProfileWeights, type RunStatus } from "../src/types/contracts";

export default function Comparer() {
  const t = useT();
  const personas = useQuery({ queryKey: ["personas"], queryFn: getPersonas });
  const [left, setLeft] = useState("amira");
  const [right, setRight] = useState("robert");
  const L = useSide(left);
  const R = useSide(right);

  if (personas.isLoading) return <Loading />;
  if (personas.error) return <Screen><ErrorState error={personas.error} /></Screen>;
  const ids = personas.data!.map((p) => p.id);
  const name = (id: string) => personas.data!.find((p) => p.id === id)?.profil.nom ?? id;
  const ready = L.result && R.result && L.pw && R.pw;
  const yn = (b: boolean) => (b ? t.common.yes : t.common.no);

  return (
    <Screen>
      <Row style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
        <Picker ids={ids} value={left} onChange={setLeft} name={name} disabled={right} />
        <View style={styles.vs}><Text style={styles.vsText}>{t.comparer.vs}</Text></View>
        <Picker ids={ids} value={right} onChange={setRight} name={name} disabled={left} />
      </Row>

      {!ready ? (
        <View style={{ gap: space.md }}>
          {L.steps ? <RunProgress steps={L.steps} /> : null}
          {R.steps ? <RunProgress steps={R.steps} /> : null}
          {!L.steps && !R.steps ? <Loading label={t.comparer.launching} /> : null}
        </View>
      ) : (
        <>
          <Section title={t.comparer.retained}>
            <Row style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
              <Ranking title={name(left)} result={L.result!} other={R.result!} />
              <Ranking title={name(right)} result={R.result!} other={L.result!} />
            </Row>
            <Text style={type.caption}>{t.comparer.onlyOne}</Text>
          </Section>

          <Section title={t.comparer.rules}>
            <Card style={{ gap: 2 }}>
              <HeaderRow a={name(left)} b={name(right)} />
              <CompareRow label={t.comparer.maxAsset} a={fmtWeight(L.pw!.hard_constraints.max_weight_per_asset)} b={fmtWeight(R.pw!.hard_constraints.max_weight_per_asset)} />
              <CompareRow label={t.comparer.maxSector} a={fmtWeight(L.pw!.hard_constraints.max_weight_per_sector)} b={fmtWeight(R.pw!.hard_constraints.max_weight_per_sector)} />
              <CompareRow label={t.comparer.maxCrypto} a={fmtWeight(L.pw!.hard_constraints.max_weight_crypto)} b={fmtWeight(R.pw!.hard_constraints.max_weight_crypto)} />
              <CompareRow label={t.comparer.esgExcl} a={yn(L.pw!.hard_constraints.esg_exclusion)} b={yn(R.pw!.hard_constraints.esg_exclusion)} />
              <CompareRow label={t.comparer.byRule} a={String(countRule(L.result!))} b={String(countRule(R.result!))} />
            </Card>
          </Section>

          <Section title={t.comparer.weights}>
            <Card style={{ gap: 2 }}>
              <HeaderRow a={name(left)} b={name(right)} />
              {CRITERIA.map((k) => (
                <CompareRow key={k} label={t.criteria[k]} a={fmtWeight(L.pw!.weights[k])} b={fmtWeight(R.pw!.weights[k])} />
              ))}
            </Card>
          </Section>
        </>
      )}
    </Screen>
  );
}

function useSide(personaId: string): { result: Explanation | null; pw: ProfileWeights | undefined; steps: RunStatus["steps"] | null } {
  const { query } = useBaseRun(personaId);
  const profile = useQuery({ queryKey: ["profile", personaId], queryFn: () => getProfile(personaId) });
  return { result: query.data?.result ?? null, pw: profile.data, steps: query.data?.status === "en_cours" ? query.data.steps : null };
}

const countRule = (r: Explanation) => r.rejected.filter((x) => x.kind === "contrainte").length;

function Picker({ ids, value, onChange, name, disabled }: { ids: string[]; value: string; onChange: (v: string) => void; name: (id: string) => string; disabled: string }) {
  return (
    <View style={{ flex: 1, gap: space.xs }}>
      {ids.map((id) => {
        const on = value === id;
        return (
          <Tap key={id} disabled={id === disabled} onPress={() => onChange(id)} accessibilityRole="radio"
            accessibilityState={{ checked: on, disabled: id === disabled }} scaleTo={0.94}
            style={[styles.pick, on && styles.pickSel, id === disabled && { opacity: 0.3 }]}>
            <Text style={[styles.pickText, on && { color: colors.primaryText }]}>{name(id)}</Text>
          </Tap>
        );
      })}
    </View>
  );
}

function Ranking({ title, result, other }: { title: string; result: Explanation; other: Explanation }) {
  const t = useT();
  const otherSet = new Set(other.items.map((i) => i.ticker));
  return (
    <Card style={{ flex: 1, padding: space.md }}>
      <Text style={type.h3}>{title}</Text>
      {result.no_recommendation ? <Text style={type.body}>{t.comparer.noPiste}</Text> : null}
      {result.items.map((i, n) => {
        const only = !otherSet.has(i.ticker);
        return (
          <View key={i.ticker} style={[styles.rankRow, only && styles.only]}>
            <Text style={type.label}>{n + 1}. {i.name}{only ? " ★" : ""}</Text>
            <Text style={type.caption}>{t.fit[i.fit]}</Text>
          </View>
        );
      })}
    </Card>
  );
}

function HeaderRow({ a, b }: { a: string; b: string }) {
  return (
    <View style={[styles.cmp, { paddingBottom: space.sm }]}>
      <View style={{ flex: 1.4 }} />
      <Text style={[type.eyebrow, styles.cell]}>{a}</Text>
      <Text style={[type.eyebrow, styles.cell]}>{b}</Text>
      <View style={{ width: 18 }} />
    </View>
  );
}

function CompareRow({ label, a, b }: { label: string; a: string; b: string }) {
  const t = useT();
  const diff = a !== b;
  return (
    <View style={[styles.cmp, diff && styles.only]} accessibilityLabel={t.comparer.a11y(label, a, b, diff)}>
      <Text style={[type.small, { flex: 1.4 }]}>{label}</Text>
      <Text style={[type.label, styles.cell]}>{a}</Text>
      <Text style={[type.label, styles.cell]}>{b}</Text>
      <Text style={[type.label, { width: 18, color: colors.warn }]}>{diff ? "≠" : ""}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pick: {
    minHeight: touchMin, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.borderStrong,
    justifyContent: "center", alignItems: "center", paddingHorizontal: space.md, backgroundColor: colors.surface,
  },
  pickSel: { backgroundColor: colors.primary, borderColor: colors.primary },
  pickText: { fontFamily, fontSize: 14, fontWeight: "700", color: colors.text },
  vs: { width: 34, height: 34, borderRadius: 17, marginTop: 5, backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center" },
  vsText: { fontFamily, fontSize: 12, fontWeight: "800", color: colors.gold },
  rankRow: { paddingVertical: space.xs, paddingHorizontal: space.xs, borderRadius: radius.sm, gap: 2 },
  only: { backgroundColor: alpha(colors.warn, 0.1) },
  cmp: { flexDirection: "row", alignItems: "center", gap: space.sm, paddingVertical: 8, paddingHorizontal: space.xs, borderRadius: radius.sm },
  cell: { flex: 1, textAlign: "center" },
});
