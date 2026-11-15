/**
 * Écran : Questionnaire en 5 questions, une par écran : objectif, horizon, tolérance au risque
 * (illustrée par une baisse), préférences, exclusions.
 */
import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { createProfile } from "../../src/api/profiles";
import { ClaimTag } from "../../src/components/ClaimTag";
import { Icon } from "../../src/components/Icon";
import { Button, Card, ErrorState, FadeIn, Row, Screen, Tap } from "../../src/components/ui";
import { useT, type Dict } from "../../src/i18n";
import { alpha, colors, radius, space, touchMin } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import type { ProfileDraft } from "../../src/types/contracts";

type Key = keyof Pick<ProfileDraft, "objectif" | "horizon" | "tolerance" | "preferences" | "exclusions">;
interface Question { key: Key; scenario?: boolean; multi?: boolean; values: string[] }

const QUESTIONS: Question[] = [
  { key: "objectif", values: ["preserver", "equilibre", "croissance"] },
  { key: "horizon", values: ["court", "moyen", "long"] },
  { key: "tolerance", scenario: true, values: ["faible", "moderee", "elevee"] },
  { key: "preferences", multi: true, values: ["esg", "technologies", "stabilite", "diversification"] },
  { key: "exclusions", multi: true, values: ["crypto", "speculatif", "controverses"] },
];

type QText = { title: string; intro?: string; options: Record<string, { label: string; detail?: string }> };
const textOf = (t: Dict, k: Key) => t.questionnaire.questions[k] as QText;

export default function Questionnaire() {
  const t = useT();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Partial<ProfileDraft>>({ preferences: [], exclusions: [] });
  const q = QUESTIONS[step];
  const qt = textOf(t, q.key);
  const value = answers[q.key];

  const create = useMutation({
    mutationFn: () => createProfile(answers as ProfileDraft),
    onSuccess: (pw) => router.replace({ pathname: "/onboarding/resume", params: { id: pw.profile_id } }),
  });

  const toggle = (v: string) => {
    if (q.multi) {
      const cur = (value as string[]) ?? [];
      setAnswers({ ...answers, [q.key]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] });
    } else {
      setAnswers({ ...answers, [q.key]: v });
    }
  };
  const answered = q.multi || typeof value === "string";
  const isLast = step === QUESTIONS.length - 1;

  return (
    <Screen>
      <View style={{ gap: space.sm }}>
        <Text style={type.eyebrow} accessibilityLiveRegion="polite">{t.questionnaire.progress(step + 1, QUESTIONS.length)}</Text>
        <View style={styles.progress}>
          {QUESTIONS.map((x, i) => (
            <View key={x.key} style={[styles.seg, i <= step && styles.segOn]} />
          ))}
        </View>
      </View>
      <Text style={type.title} accessibilityRole="header">{qt.title}</Text>
      {qt.intro ? (
        <Card style={q.scenario ? { backgroundColor: colors.scenarioBg, borderColor: alpha(colors.scenario, 0.3) } : undefined}>
          {q.scenario ? <ClaimTag kind="SCENARIO" /> : null}
          <Text style={type.body}>{qt.intro}</Text>
          {q.scenario ? <DropIllustration /> : null}
        </Card>
      ) : null}

      <View style={{ gap: space.sm }}>
        {q.values.map((v, i) => {
          const o = qt.options[v];
          const sel = q.multi ? ((value as string[]) ?? []).includes(v) : value === v;
          return (
            <FadeIn key={`${q.key}-${v}`} index={i}>
              <Tap
                onPress={() => toggle(v)}
                accessibilityRole={q.multi ? "checkbox" : "radio"}
                accessibilityState={{ checked: sel }}
                scaleTo={0.97}
                style={({ hovered }) => [styles.option, hovered && !sel && styles.optionHover, sel && styles.optionSel]}
              >
                <View style={[q.multi ? styles.box : styles.radio, sel && styles.markOn]}>
                  {sel ? (q.multi ? <Icon name="check" size={14} color={colors.primaryText} strokeWidth={3} /> : <View style={styles.radioDot} />) : null}
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={type.h3}>{o.label}</Text>
                  {o.detail ? <Text style={type.small}>{o.detail}</Text> : null}
                </View>
              </Tap>
            </FadeIn>
          );
        })}
      </View>

      {create.error ? <ErrorState error={create.error} onRetry={() => create.mutate()} /> : null}
      <Row style={{ justifyContent: "space-between", marginTop: space.sm }}>
        <Button label={t.questionnaire.prev} variant="ghost" disabled={step === 0} onPress={() => setStep(step - 1)} />
        <Button
          label={isLast ? (create.isPending ? t.questionnaire.finishing : t.questionnaire.finish) : t.questionnaire.next}
          disabled={!answered || create.isPending}
          onPress={() => (isLast ? create.mutate() : setStep(step + 1))}
        />
      </Row>
    </Screen>
  );
}

/** Illustration de la baisse : 10 000 $ → 8 000 $. */
function DropIllustration() {
  const t = useT();
  return (
    <View style={styles.drop} accessibilityLabel={t.questionnaire.dropA11y}>
      <View style={{ alignItems: "center", gap: 4 }}>
        <View style={[styles.bar, { height: 80 }]} />
        <Text style={type.caption}>{t.questionnaire.dropFrom}</Text>
      </View>
      <View style={{ alignItems: "center", gap: 2 }}>
        <Icon name="trendingDown" size={22} color={colors.bad} />
        <Text style={[type.h3, { color: colors.bad }]}>{t.questionnaire.dropPct}</Text>
      </View>
      <View style={{ alignItems: "center", gap: 4 }}>
        <View style={[styles.bar, { height: 64, backgroundColor: colors.bad }]} />
        <Text style={type.caption}>{t.questionnaire.dropTo}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  progress: { flexDirection: "row", gap: 6 },
  seg: { flex: 1, height: 5, borderRadius: 3, backgroundColor: colors.surfaceRaised },
  segOn: { backgroundColor: colors.primary },
  option: {
    flexDirection: "row", alignItems: "center", gap: space.md, minHeight: touchMin + 16,
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, padding: space.md,
  },
  optionSel: { borderColor: colors.primary, backgroundColor: alpha(colors.primary, 0.1) },
  optionHover: { borderColor: colors.borderStrong },
  radio: { width: 24, height: 24, borderRadius: 12, borderWidth: 2, borderColor: colors.borderStrong, alignItems: "center", justifyContent: "center" },
  box: { width: 24, height: 24, borderRadius: 7, borderWidth: 2, borderColor: colors.borderStrong, alignItems: "center", justifyContent: "center" },
  markOn: { borderColor: colors.primary, backgroundColor: colors.primary },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primaryText },
  drop: { flexDirection: "row", alignItems: "flex-end", justifyContent: "center", gap: space.xl, paddingTop: space.sm },
  bar: { width: 44, borderRadius: radius.sm, backgroundColor: colors.primary },
});
