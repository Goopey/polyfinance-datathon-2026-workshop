/**
 * Écran : « Voici comment nous avons compris votre profil » — poids et règles en clair, modifiables.
 * C'est la sortie de l'agent de pondération (ProfileWeights). Une règle écarte ; un poids classe.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { createProfile, getProfile } from "../../src/api/profiles";
import { ClaimTag } from "../../src/components/ClaimTag";
import { Button, Card, ErrorState, Loading, Row, Screen, Section } from "../../src/components/ui";
import { fmtWeight } from "../../src/format";
import { fr } from "../../src/i18n/fr";
import { useProfileStore } from "../../src/store/profile";
import { colors, radius, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import { CRITERIA, type Criterion, type CriterionMap, type ProfileWeights } from "../../src/types/contracts";

const STEP = 0.05;

export default function ResumeProfil() {
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

  if (profile.isLoading || !weights) return profile.error ? <Screen><ErrorState error={profile.error} /></Screen> : <Loading />;
  const pw = profile.data!;
  const total = CRITERIA.reduce((s, k) => s + weights[k], 0) || 1;
  const bump = (k: Criterion, d: number) =>
    setWeights({ ...weights, [k]: Math.max(0, Math.round((weights[k] + d) * 100) / 100) });
  const hc = pw.hard_constraints;

  return (
    <Screen>
      <View style={{ gap: space.xs }}>
        <Text style={type.title}>Voici comment nous avons compris votre profil</Text>
        <Text style={type.body}>{pw.summary}</Text>
      </View>

      <Section title="Règles (elles écartent)">
        <Card>
          <Rule text={`Au plus ${fmtWeight(hc.max_weight_per_asset)} du panier simulé sur un même actif.`} />
          <Rule text={`Au plus ${fmtWeight(hc.max_weight_per_sector)} sur un même secteur.`} />
          <Rule text={hc.max_weight_crypto === 0 ? "Aucun cryptoactif." : `Au plus ${fmtWeight(hc.max_weight_crypto)} en cryptoactifs.`} />
          {hc.esg_exclusion ? <Rule text="Écarter les entreprises à controverse environnementale ou sociale documentée." /> : null}
          {hc.speculatif === "exclu" ? <Rule text="Écarter les placements hautement spéculatifs." /> : null}
          {hc.speculatif === "signalé" ? <Rule text="Signaler les placements hautement spéculatifs (ils ne sont pas écartés)." /> : null}
          {hc.excluded_asset_classes.filter((c) => c !== "crypto").map((c) => (
            <Rule key={c} text={`Classe d'actifs exclue : ${fr.assetClass[c] ?? c}.`} />
          ))}
        </Card>
      </Section>

      <Section title="Poids (ils classent)">
        <Text style={type.small}>Touchez − ou + pour modifier un poids. Les poids sont ramenés à 100 % au total.</Text>
        <Card>
          {CRITERIA.map((k) => {
            const share = weights[k] / total;
            return (
              <View key={k} style={styles.weightRow}>
                <View style={{ flex: 1, gap: 4 }}>
                  <Row style={{ justifyContent: "space-between" }}>
                    <Text style={type.label}>{fr.criteria[k]}</Text>
                    <Text style={type.small}>{fmtWeight(share)}</Text>
                  </Row>
                  <View style={styles.track}>
                    <View style={[styles.fill, { width: `${share * 100}%` }]} />
                  </View>
                </View>
                <Stepper label="−" onPress={() => bump(k, -STEP)} a11y={`Diminuer ${fr.criteria[k]}`} />
                <Stepper label="+" onPress={() => bump(k, STEP)} a11y={`Augmenter ${fr.criteria[k]}`} />
              </View>
            );
          })}
          <Row>
            <ClaimTag kind="HYPOTHESE" />
            <Text style={[type.caption, { flex: 1 }]}>Valeurs de départ fixées par l'équipe, à calibrer.</Text>
          </Row>
        </Card>
      </Section>

      <Section title="Pourquoi ces valeurs">
        <Card>
          {pw.rationale.map((r) => (
            <View key={r.field + r.because} style={{ gap: 4 }}>
              <Text style={type.body}>{r.because}</Text>
              {r.claim_kind ? <ClaimTag kind={r.claim_kind} /> : null}
            </View>
          ))}
        </Card>
      </Section>

      {pw.missing_information.length > 0 ? (
        <Card style={{ backgroundColor: colors.warnBg, borderColor: colors.warnBg }}>
          <Text style={type.h3}>? Informations manquantes</Text>
          {pw.missing_information.map((m) => <Text key={m} style={type.body}>{m}</Text>)}
        </Card>
      ) : null}

      {confirm.error ? <ErrorState error={confirm.error} /> : null}
      <Button
        label={confirm.isPending ? "Enregistrement…" : modified ? "Confirmer les poids modifiés" : "Confirmer et voir les pistes"}
        disabled={confirm.isPending}
        onPress={() => confirm.mutate()}
      />
      {modified ? <Button label="Revenir aux poids proposés" variant="ghost" onPress={() => setWeights(pw.weights)} /> : null}
      <Button label="Choisir un autre profil" variant="ghost" onPress={() => router.replace("/onboarding")} />
    </Screen>
  );
}

function Rule({ text }: { text: string }) {
  return (
    <Row style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
      <Text style={[type.body, { color: colors.primary }]}>▪</Text>
      <Text style={[type.body, { flex: 1 }]}>{text}</Text>
    </Row>
  );
}

function Stepper({ label, onPress, a11y }: { label: string; onPress: () => void; a11y: string }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={a11y} style={({ pressed }) => [styles.stepper, pressed && { opacity: 0.7 }]}>
      <Text style={styles.stepperText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  weightRow: { flexDirection: "row", alignItems: "center", gap: space.sm, paddingVertical: space.xs },
  track: { height: 10, borderRadius: radius.sm, backgroundColor: colors.surfaceMuted, overflow: "hidden" },
  fill: { height: 10, backgroundColor: colors.primary },
  stepper: {
    width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: colors.primary,
    alignItems: "center", justifyContent: "center",
  },
  stepperText: { fontSize: 22, color: colors.primary, fontWeight: "700", lineHeight: 26 },
});
