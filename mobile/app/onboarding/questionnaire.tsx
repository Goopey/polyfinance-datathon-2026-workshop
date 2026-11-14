/**
 * Écran : Questionnaire en 5 questions, une par écran : objectif, horizon, tolérance au risque
 * (illustrée par une baisse simulée), préférences, exclusions.
 */
import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { createProfile } from "../../src/api/profiles";
import { ClaimTag } from "../../src/components/ClaimTag";
import { Button, Card, ErrorState, Row, Screen } from "../../src/components/ui";
import { colors, radius, space, touchMin } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import type { ProfileDraft } from "../../src/types/contracts";

type Option = { value: string; label: string; detail?: string };
interface Question {
  key: keyof Pick<ProfileDraft, "objectif" | "horizon" | "tolerance" | "preferences" | "exclusions">;
  title: string;
  intro?: string;
  scenario?: boolean;
  multi?: boolean;
  options: Option[];
}

const QUESTIONS: Question[] = [
  {
    key: "objectif", title: "Quel est l'objectif de ce profil ?",
    options: [
      { value: "preserver", label: "Préserver le capital", detail: "Limiter les baisses avant tout" },
      { value: "equilibre", label: "Croître de façon équilibrée", detail: "Un compromis entre croissance et stabilité" },
      { value: "croissance", label: "Faire croître le capital", detail: "Accepter des variations pour viser la croissance" },
    ],
  },
  {
    key: "horizon", title: "Dans combien de temps ce capital fictif serait-il utilisé ?",
    options: [
      { value: "court", label: "Moins de 5 ans" },
      { value: "moyen", label: "De 5 à 12 ans" },
      { value: "long", label: "Plus de 12 ans" },
    ],
  },
  {
    key: "tolerance", title: "Comment réagiriez-vous à cette baisse ?", scenario: true,
    intro: "Imaginez un panier fictif de 10 000 $ qui descend à 8 000 $ en quelques mois.",
    options: [
      { value: "faible", label: "Je serais très inquiet", detail: "Tolérance au risque faible" },
      { value: "moderee", label: "Inconfortable, mais j'attendrais", detail: "Tolérance au risque modérée" },
      { value: "elevee", label: "Ça fait partie du jeu", detail: "Tolérance au risque élevée" },
    ],
  },
  {
    key: "preferences", title: "Qu'est-ce qui compte pour ce profil ?", multi: true,
    intro: "Plusieurs choix possibles, ou aucun.",
    options: [
      { value: "esg", label: "Critères environnementaux et sociaux (ESG)" },
      { value: "technologies", label: "Technologies et innovation" },
      { value: "stabilite", label: "Entreprises établies et stables" },
      { value: "diversification", label: "Ne pas tout miser sur un seul secteur" },
    ],
  },
  {
    key: "exclusions", title: "Que faut-il écarter ?", multi: true,
    intro: "Une exclusion est une règle : elle écarte, elle ne fait pas que déclasser.",
    options: [
      { value: "crypto", label: "Cryptoactifs" },
      { value: "speculatif", label: "Placements hautement spéculatifs" },
      { value: "controverses", label: "Entreprises à controverse documentée" },
      { value: "actions", label: "Actions individuelles" },
      { value: "fnb", label: "Fonds négociés en bourse (FNB)" },
    ],
  },
];

export default function Questionnaire() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Partial<ProfileDraft>>({ preferences: [], exclusions: [] });
  const q = QUESTIONS[step];
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
      <Text style={type.small} accessibilityLiveRegion="polite">
        Question {step + 1} sur {QUESTIONS.length}
      </Text>
      <View style={styles.progress}>
        <View style={[styles.progressFill, { width: `${((step + 1) / QUESTIONS.length) * 100}%` }]} />
      </View>
      <Text style={type.title} accessibilityRole="header">{q.title}</Text>
      {q.intro ? (
        <Card style={q.scenario ? { backgroundColor: colors.scenarioBg, borderColor: colors.scenarioBg } : undefined}>
          {q.scenario ? <ClaimTag kind="SCENARIO" /> : null}
          <Text style={type.body}>{q.intro}</Text>
          {q.scenario ? <DropIllustration /> : null}
        </Card>
      ) : null}

      <View style={{ gap: space.sm }}>
        {q.options.map((o) => {
          const sel = q.multi ? ((value as string[]) ?? []).includes(o.value) : value === o.value;
          return (
            <Pressable
              key={o.value}
              onPress={() => toggle(o.value)}
              accessibilityRole={q.multi ? "checkbox" : "radio"}
              accessibilityState={{ checked: sel }}
              style={[styles.option, sel && styles.optionSel]}
            >
              <Text style={[styles.check, sel && { color: colors.primary }]}>{q.multi ? (sel ? "☑" : "☐") : sel ? "◉" : "○"}</Text>
              <View style={{ flex: 1 }}>
                <Text style={type.h3}>{o.label}</Text>
                {o.detail ? <Text style={type.small}>{o.detail}</Text> : null}
              </View>
            </Pressable>
          );
        })}
      </View>

      {create.error ? <ErrorState error={create.error} onRetry={() => create.mutate()} /> : null}
      <Row style={{ justifyContent: "space-between" }}>
        <Button label="Précédent" variant="ghost" disabled={step === 0} onPress={() => setStep(step - 1)} />
        <Button
          label={isLast ? (create.isPending ? "Analyse du profil…" : "Voir mon profil") : "Suivant"}
          disabled={!answered || create.isPending}
          onPress={() => (isLast ? create.mutate() : setStep(step + 1))}
        />
      </Row>
      <Text style={type.caption}>Profil fictif : aucune donnée personnelle n'est demandée ni conservée.</Text>
    </Screen>
  );
}

/** Illustration de la baisse simulée : 10 000 $ → 8 000 $. */
function DropIllustration() {
  return (
    <View style={styles.drop} accessibilityLabel="Barre de 10 000 dollars, puis barre de 8 000 dollars">
      <View style={{ alignItems: "center", gap: 4 }}>
        <View style={[styles.bar, { height: 80 }]} />
        <Text style={type.caption}>10 000 $</Text>
      </View>
      <Text style={[type.h3, { color: colors.bad }]}>↘ −20 %</Text>
      <View style={{ alignItems: "center", gap: 4 }}>
        <View style={[styles.bar, { height: 64, backgroundColor: colors.bad }]} />
        <Text style={type.caption}>8 000 $</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  progress: { height: 6, borderRadius: 3, backgroundColor: colors.surfaceMuted, overflow: "hidden" },
  progressFill: { height: 6, backgroundColor: colors.primary },
  option: {
    flexDirection: "row", alignItems: "center", gap: space.md, minHeight: touchMin + 12,
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, padding: space.md,
  },
  optionSel: { borderColor: colors.primary, backgroundColor: "#EEF3FF" },
  check: { fontSize: 22, color: colors.textMuted, width: 26 },
  drop: { flexDirection: "row", alignItems: "flex-end", justifyContent: "center", gap: space.xl, paddingTop: space.sm },
  bar: { width: 44, borderRadius: radius.sm, backgroundColor: colors.primary },
});
