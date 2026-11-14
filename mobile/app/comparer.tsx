/**
 * Écran : Comparer deux profils côte à côte sur le même univers et la même date :
 * classements, règles appliquées, différences surlignées (scénario S12 ; extra n° 2, utile pour la vidéo).
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { getPersonas, getProfile } from "../src/api/profiles";
import { RunProgress } from "../src/components/RunProgress";
import { Card, ErrorState, Loading, Row, Screen, Section } from "../src/components/ui";
import { fmtWeight } from "../src/format";
import { useBaseRun } from "../src/hooks/useBaseRun";
import { fr } from "../src/i18n/fr";
import { colors, radius, space, touchMin } from "../src/theme/tokens";
import { type } from "../src/theme/typography";
import { CRITERIA, type Explanation, type ProfileWeights, type RunStatus } from "../src/types/contracts";

export default function Comparer() {
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

  return (
    <Screen>
      <Text style={type.body}>Même univers, même date, deux profils : les différences viennent d'un poids ou d'une règle nommée.</Text>
      <Row style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
        <Picker ids={ids} value={left} onChange={setLeft} name={name} disabled={right} />
        <Text style={[type.h3, { paddingTop: 12 }]}>vs</Text>
        <Picker ids={ids} value={right} onChange={setRight} name={name} disabled={left} />
      </Row>

      {!ready ? (
        <View style={{ gap: space.md }}>
          {L.steps ? <RunProgress steps={L.steps} /> : null}
          {R.steps ? <RunProgress steps={R.steps} /> : null}
          {!L.steps && !R.steps ? <Loading label="Lancement des analyses…" /> : null}
        </View>
      ) : (
        <>
          <Section title="Pistes retenues">
            <Row style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
              <Ranking title={name(left)} result={L.result!} other={R.result!} />
              <Ranking title={name(right)} result={R.result!} other={L.result!} />
            </Row>
            <Text style={type.caption}>★ = présente chez un seul des deux profils.</Text>
          </Section>

          <Section title="Règles appliquées">
            <Card>
              <CompareRow label="Part max. par actif" a={fmtWeight(L.pw!.hard_constraints.max_weight_per_asset)} b={fmtWeight(R.pw!.hard_constraints.max_weight_per_asset)} />
              <CompareRow label="Part max. par secteur" a={fmtWeight(L.pw!.hard_constraints.max_weight_per_sector)} b={fmtWeight(R.pw!.hard_constraints.max_weight_per_sector)} />
              <CompareRow label="Part max. en crypto" a={fmtWeight(L.pw!.hard_constraints.max_weight_crypto)} b={fmtWeight(R.pw!.hard_constraints.max_weight_crypto)} />
              <CompareRow label="Exclusion sur controverse" a={L.pw!.hard_constraints.esg_exclusion ? "oui" : "non"} b={R.pw!.hard_constraints.esg_exclusion ? "oui" : "non"} />
              <CompareRow label="Écartées par une règle" a={String(countRule(L.result!))} b={String(countRule(R.result!))} />
            </Card>
          </Section>

          <Section title="Poids">
            <Card>
              {CRITERIA.map((k) => (
                <CompareRow key={k} label={fr.criteria[k]} a={fmtWeight(L.pw!.weights[k])} b={fmtWeight(R.pw!.weights[k])} />
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
      {ids.map((id) => (
        <Pressable key={id} disabled={id === disabled} onPress={() => onChange(id)} accessibilityRole="radio"
          accessibilityState={{ checked: value === id, disabled: id === disabled }}
          style={[styles.pick, value === id && styles.pickSel, id === disabled && { opacity: 0.35 }]}>
          <Text style={[type.label, value === id && { color: colors.primaryText }]}>{value === id ? "◉" : "○"} {name(id)}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function Ranking({ title, result, other }: { title: string; result: Explanation; other: Explanation }) {
  const otherSet = new Set(other.items.map((i) => i.ticker));
  return (
    <Card style={{ flex: 1, padding: space.md }}>
      <Text style={type.h3}>{title}</Text>
      {result.no_recommendation ? <Text style={type.body}>Aucune piste</Text> : null}
      {result.items.map((i, n) => {
        const only = !otherSet.has(i.ticker);
        return (
          <View key={i.ticker} style={[styles.rankRow, only && styles.only]}>
            <Text style={type.label}>{n + 1}. {i.name}{only ? " ★" : ""}</Text>
            <Text style={type.caption}>{fr.fit[i.fit]}</Text>
          </View>
        );
      })}
    </Card>
  );
}

function CompareRow({ label, a, b }: { label: string; a: string; b: string }) {
  const diff = a !== b;
  return (
    <View style={[styles.cmp, diff && styles.only]} accessibilityLabel={`${label} : ${a} contre ${b}${diff ? ", différent" : ""}`}>
      <Text style={[type.small, { flex: 1.4 }]}>{label}</Text>
      <Text style={[type.label, styles.cell]}>{a}</Text>
      <Text style={[type.label, styles.cell]}>{b}</Text>
      <Text style={[type.caption, { width: 18 }]}>{diff ? "≠" : ""}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pick: {
    minHeight: touchMin, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.primary,
    justifyContent: "center", paddingHorizontal: space.md, backgroundColor: colors.surface,
  },
  pickSel: { backgroundColor: colors.primary },
  rankRow: { paddingVertical: space.xs, paddingHorizontal: space.xs, borderRadius: radius.sm },
  only: { backgroundColor: colors.warnBg },
  cmp: { flexDirection: "row", alignItems: "center", gap: space.sm, paddingVertical: 6, paddingHorizontal: space.xs, borderRadius: radius.sm },
  cell: { flex: 1, textAlign: "center" },
});
