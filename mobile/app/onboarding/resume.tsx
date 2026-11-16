/**
 * Écran : « Voici comment nous avons compris votre profil » — poids et règles en clair, modifiables.
 * C'est la sortie de l'agent de pondération (ProfileWeights). Une règle écarte ; un poids classe.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Animated, Platform, StyleSheet, Text, View } from "react-native";
import { createProfile, getProfile } from "../../src/api/profiles";
import { Icon, type IconName } from "../../src/components/Icon";
import {
  Button, Card, Collapsible, ErrorState, FadeIn, Loading, Row, Screen, Section, Tap, settle, webTransition,
} from "../../src/components/ui";
import { fmtWeight } from "../../src/format";
import { useT } from "../../src/i18n";
import { useTx } from "../../src/i18n/data";
import { useProfileStore } from "../../src/store/profile";
import { alpha, colors, radius, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import { CRITERIA, type Criterion, type CriterionMap, type ProfileWeights } from "../../src/types/contracts";

const STEP = 0.05;

export default function ResumeProfil() {
  const t = useT();
  const tx = useTx();
  const { id } = useLocalSearchParams<{ id: string }>();
  const setProfile = useProfileStore((s) => s.setProfile);
  const profile = useQuery({ queryKey: ["profile", id], queryFn: () => getProfile(id!), enabled: !!id });
  const [weights, setWeights] = useState<CriterionMap | null>(null);

  useEffect(() => {
    if (profile.data) setWeights(profile.data.weights);
  }, [profile.data]);

  const modified = !!weights && !!profile.data && CRITERIA.some((k) => Math.abs(weights[k] - profile.data!.weights[k]) > 1e-6);

  const confirm = useMutation({
    mutationFn: async (): Promise<ProfileWeights> => {
      if (!modified) return profile.data!;
      return createProfile({
        base_persona: id!, objectif: "equilibre", horizon: "moyen", tolerance: "moderee",
        preferences: [], exclusions: [], weights_override: weights!,
      });
    },
    onSuccess: (pw) => {
      setProfile(pw);
      router.replace("/(tabs)");
    },
  });

  if (profile.isLoading || !weights) {
    if (!profile.error) return <Loading />;
    return (
      <Screen>
        <ErrorState error={profile.error} onRetry={() => profile.refetch()} />
        <Button label={t.resume.chooseOther} variant="secondary" onPress={() => router.replace("/onboarding")} />
      </Screen>
    );
  }
  const pw = profile.data!;
  const total = CRITERIA.reduce((s, k) => s + weights[k], 0) || 1;
  const bump = (k: Criterion, d: number) =>
    setWeights({ ...weights, [k]: Math.max(0, Math.round((weights[k] + d) * 100) / 100) });
  const hc = pw.hard_constraints;
  // Réponses contradictoires du questionnaire, tranchées par la lecture la plus prudente (backend, audit C1).
  const conflicts = pw.rationale.filter((r) => r.field === "tolerance");
  const reasons = pw.rationale.filter((r) => r.field !== "tolerance");

  return (
    <Screen>
      <FadeIn style={{ gap: space.sm }}>
        <Text style={type.title}>{t.resume.title}</Text>
        <Text style={[type.body, { color: colors.textMuted }]}>{tx(pw.summary)}</Text>
      </FadeIn>

      {conflicts.length > 0 ? (
        <Card style={{ backgroundColor: colors.warnBg, borderColor: alpha(colors.warn, 0.4) }}>
          <Row>
            <Icon name="scale" size={18} color={colors.warn} />
            <Text style={[type.h3, { color: colors.warn, flex: 1 }]}>{t.resume.conflictTitle}</Text>
          </Row>
          {conflicts.map((r) => <Text key={r.because} style={type.body}>{tx(r.because)}</Text>)}
        </Card>
      ) : null}

      <Section title={t.resume.rulesTitle}>
        <Card>
          <Rule text={t.resume.ruleMaxAsset(fmtWeight(hc.max_weight_per_asset))} />
          <Rule text={t.resume.ruleMaxSector(fmtWeight(hc.max_weight_per_sector))} />
          <Rule icon={hc.max_weight_crypto === 0 ? "ban" : "check"} text={hc.max_weight_crypto === 0 ? t.resume.ruleNoCrypto : t.resume.ruleMaxCrypto(fmtWeight(hc.max_weight_crypto))} />
          {hc.esg_exclusion ? <Rule icon="ban" text={t.resume.ruleEsg} /> : null}
          {hc.speculatif === "exclu" ? <Rule icon="ban" text={t.resume.ruleSpecExcluded} /> : null}
          {hc.speculatif === "signalé" ? <Rule icon="alert" text={t.resume.ruleSpecFlagged} /> : null}
          {hc.excluded_asset_classes.filter((c) => c !== "crypto").map((c) => (
            <Rule key={c} icon="ban" text={t.resume.ruleClass(t.assetClass[c] ?? c)} />
          ))}
        </Card>
      </Section>

      <Section title={t.resume.weightsTitle} hint={t.resume.weightsHint}>
        <Card style={{ gap: space.md }}>
          {CRITERIA.map((k) => {
            const share = weights[k] / total;
            return (
              <View key={k} style={styles.weightRow}>
                <View style={{ flex: 1, gap: 6 }}>
                  <Row style={{ justifyContent: "space-between" }}>
                    <Text style={type.label}>{t.criteria[k]}</Text>
                    <Text style={[type.label, { color: colors.mint }]}>{fmtWeight(share)}</Text>
                  </Row>
                  <WeightBar share={share} />
                </View>
                <Stepper icon="minus" onPress={() => bump(k, -STEP)} a11y={t.resume.decrease(t.criteria[k])} />
                <Stepper icon="plus" onPress={() => bump(k, STEP)} a11y={t.resume.increase(t.criteria[k])} />
              </View>
            );
          })}
        </Card>
      </Section>

      {reasons.length > 0 ? (
        <Collapsible title={t.resume.whyTitle} summary={t.resume.whySummary(reasons.length)} icon="info">
          {reasons.map((r) => (
            <View key={r.field + r.because} style={styles.reason}>
              <View style={styles.reasonDot} />
              <Text style={[type.body, { flex: 1 }]}>{tx(r.because)}</Text>
            </View>
          ))}
        </Collapsible>
      ) : null}

      {/* Avertissement fixe (remplace les « informations manquantes » rédigées par l'agent, texte libre
          différent à chaque exécution) : ce que l'analyse ne prend pas en compte, vrai pour tout profil. */}
      <Card style={{ backgroundColor: colors.infoBg, borderColor: alpha(colors.info, 0.3) }}>
        <Row>
          <Icon name="info" size={18} color={colors.info} />
          <Text style={[type.h3, { color: colors.info }]}>{t.resume.disclaimerTitle}</Text>
        </Row>
        <Text style={type.body}>{t.resume.disclaimer}</Text>
      </Card>

      {confirm.error ? <ErrorState error={confirm.error} /> : null}
      <View style={{ gap: space.sm, marginTop: space.sm }}>
        <Button
          label={confirm.isPending ? t.resume.saving : modified ? t.resume.confirmModified : t.resume.confirm}
          icon={confirm.isPending ? undefined : "arrowRight"}
          disabled={confirm.isPending}
          onPress={() => confirm.mutate()}
        />
        {modified ? <Button label={t.resume.revert} variant="secondary" icon="refresh" onPress={() => setWeights(pw.weights)} /> : null}
        <Button label={t.resume.chooseOther} variant="ghost" onPress={() => router.replace("/onboarding")} />
      </View>
    </Screen>
  );
}

function Rule({ text, icon = "check" }: { text: string; icon?: IconName }) {
  const c = icon === "ban" ? colors.bad : icon === "alert" ? colors.warn : colors.good;
  return (
    <Row style={{ alignItems: "flex-start", flexWrap: "nowrap", paddingVertical: 2 }}>
      <View style={[styles.ruleIcon, { backgroundColor: alpha(c, 0.12) }]}>
        <Icon name={icon} size={14} color={c} strokeWidth={2.6} />
      </View>
      <Text style={[type.body, { flex: 1 }]}>{text}</Text>
    </Row>
  );
}

function Stepper({ icon, onPress, a11y }: { icon: IconName; onPress: () => void; a11y: string }) {
  return (
    <Tap onPress={onPress} accessibilityRole="button" accessibilityLabel={a11y} scaleTo={0.85}
      style={({ pressed }) => [styles.stepper, pressed && styles.stepperOn]}>
      <Icon name={icon} size={18} color={colors.mint} strokeWidth={2.6} />
    </Tap>
  );
}

/** Barre de poids proportionnelle à 100 %, qui glisse vers sa nouvelle longueur à chaque ajustement. */
function WeightBar({ share }: { share: number }) {
  const v = useRef(new Animated.Value(share)).current;
  useEffect(() => {
    if (Platform.OS === "web") return;
    settle(Animated.spring(v, { toValue: share, useNativeDriver: false, speed: 18, bounciness: 6 }), v, share);
  }, [v, share]);
  if (Platform.OS === "web") {
    // Web : largeur exacte et transition CSS (voir components/ui.tsx).
    return (
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.max(0, Math.min(1, share)) * 100}%` }, webTransition]} />
      </View>
    );
  }
  const width = v.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"], extrapolate: "clamp" });
  return (
    <View style={styles.track}>
      <Animated.View style={[styles.fill, { width }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  weightRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  track: { height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceRaised, overflow: "hidden" },
  fill: { height: 8, borderRadius: radius.pill, backgroundColor: colors.primary },
  ruleIcon: { width: 24, height: 24, borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 0 },
  stepper: {
    width: 44, height: 44, borderRadius: 22, borderWidth: 1, borderColor: colors.borderStrong,
    backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center",
  },
  stepperOn: { backgroundColor: alpha(colors.mint, 0.16), borderColor: colors.mint },
  reason: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  reasonDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.primary, marginTop: 9 },
});
