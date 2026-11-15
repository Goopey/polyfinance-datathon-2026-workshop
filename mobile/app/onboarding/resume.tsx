/**
 * Écran : « Voici comment nous avons compris votre profil » — poids et règles en clair, modifiables.
 * C'est la sortie de l'agent de pondération (ProfileWeights). Une règle écarte ; un poids classe.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { createProfile, getProfile } from "../../src/api/profiles";
import { Icon, type IconName } from "../../src/components/Icon";
import { Button, Card, Collapsible, ErrorState, FadeIn, Loading, Row, Screen, Section, Tap } from "../../src/components/ui";
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

  return (
    <Screen>
      <FadeIn style={{ gap: space.sm }}>
        <Text style={type.title}>{t.resume.title}</Text>
        <Text style={[type.body, { color: colors.textMuted }]}>{tx(pw.summary)}</Text>
      </FadeIn>

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

      {pw.rationale.length > 0 ? (
        <Collapsible title={t.resume.whyTitle} summary={t.resume.whySummary(pw.rationale.length)} icon="info">
          {pw.rationale.map((r) => (
            <View key={r.field + r.because} style={styles.reason}>
              <View style={styles.reasonDot} />
              <Text style={[type.body, { flex: 1 }]}>{tx(r.because)}</Text>
            </View>
          ))}
        </Collapsible>
      ) : null}

      {pw.missing_information.length > 0 ? (
        <Card style={{ backgroundColor: colors.warnBg, borderColor: alpha(colors.warn, 0.3) }}>
          <Row>
            <Icon name="help" size={18} color={colors.warn} />
            <Text style={[type.h3, { color: colors.warn }]}>{t.resume.missingTitle}</Text>
          </Row>
          {pw.missing_information.map((m) => <Text key={m} style={type.body}>{tx(m)}</Text>)}
        </Card>
      ) : null}

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
    Animated.spring(v, { toValue: share, useNativeDriver: false, speed: 18, bounciness: 6 }).start();
  }, [v, share]);
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
