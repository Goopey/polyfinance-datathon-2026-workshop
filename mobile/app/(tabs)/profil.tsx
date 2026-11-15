/**
 * Écran : Profil courant, niveau de lecture Simple / Avancé, langue, changement de profil, accès aux écrans annexes.
 */
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { getProfile } from "../../src/api/profiles";
import { LangToggle } from "../../src/components/HeaderActions";
import { Icon, type IconName } from "../../src/components/Icon";
import { Button, Card, Row, Screen, Section, Tap } from "../../src/components/ui";
import { fmtWeight } from "../../src/format";
import { useT } from "../../src/i18n";
import { useTx } from "../../src/i18n/data";
import { useProfileStore } from "../../src/store/profile";
import { useSettings, type ReadingMode } from "../../src/store/settings";
import { alpha, colors, radius, space, touchMin } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";
import { CRITERIA } from "../../src/types/contracts";

export default function Profil() {
  const t = useT();
  const tx = useTx();
  const { profileId, summary, reset } = useProfileStore();
  const { mode, setMode } = useSettings();
  const profile = useQuery({ queryKey: ["profile", profileId], queryFn: () => getProfile(profileId!), enabled: !!profileId });

  return (
    <Screen>
      <Section title={t.profil.currentTitle}>
        <Card style={{ gap: space.md }}>
          <Text style={type.h3}>{summary ? tx(summary) : t.profil.none}</Text>
          {profile.data ? (
            <View style={styles.chips}>
              {CRITERIA.filter((k) => profile.data!.weights[k] > 0).map((k) => (
                <View key={k} style={styles.chip}>
                  <Text style={styles.chipLabel}>{t.criteria[k]}</Text>
                  <Text style={styles.chipValue}>{fmtWeight(profile.data!.weights[k])}</Text>
                </View>
              ))}
            </View>
          ) : null}
          <View style={{ gap: space.sm }}>
            {profileId ? (
              <Button label={t.profil.seeWeights} variant="secondary" icon="sliders"
                onPress={() => router.push({ pathname: "/onboarding/resume", params: { id: profileId } })} />
            ) : null}
            <Button label={t.profil.change} variant="ghost" icon="refresh" onPress={() => { reset(); router.replace("/onboarding"); }} />
          </View>
        </Card>
      </Section>

      <Section title={t.profil.readingTitle} hint={t.profil.readingHint}>
        <View style={styles.segment} accessibilityRole="radiogroup">
          {(["simple", "avance"] as ReadingMode[]).map((m) => {
            const on = mode === m;
            return (
              <Tap key={m} onPress={() => setMode(m)} accessibilityRole="radio" accessibilityState={{ checked: on }}
                scaleTo={0.95} style={[styles.segBtn, on && styles.segSel]}>
                <Text style={[styles.segText, on && { color: colors.primaryText }]}>
                  {m === "simple" ? t.profil.simple : t.profil.advanced}
                </Text>
              </Tap>
            );
          })}
        </View>
      </Section>

      <Section title={t.profil.langTitle} right={<LangToggle />}>
        <View />
      </Section>

      <Section title={t.profil.moreTitle}>
        <Card style={{ padding: 0, gap: 0 }}>
          <NavRow icon="layers" label={t.nav.comparer} onPress={() => router.push("/comparer")} />
          <NavRow icon="database" label={t.nav.donnees} onPress={() => router.push("/donnees")} last />
        </Card>
      </Section>

      <Card style={{ backgroundColor: alpha(colors.mint, 0.04) }}>
        <Row>
          <Icon name="info" size={18} color={colors.textMuted} />
          <Text style={type.h3}>{t.profil.aboutTitle}</Text>
        </Row>
        <Text style={[type.small, { color: colors.text }]}>{t.profil.aboutBody(t.appName)}</Text>
      </Card>
    </Screen>
  );
}

function NavRow({ icon, label, onPress, last }: { icon: IconName; label: string; onPress: () => void; last?: boolean }) {
  return (
    <Tap onPress={onPress} accessibilityRole="button" scaleTo={0.98}
      style={({ pressed, hovered }) => [styles.navRow, !last && styles.navDivider, (pressed || hovered) && { backgroundColor: colors.surfaceRaised }]}>
      <View style={styles.navIcon}>
        <Icon name={icon} size={18} color={colors.mint} />
      </View>
      <Text style={[type.body, { flex: 1, fontWeight: "600" }]}>{label}</Text>
      <Icon name="chevronRight" size={20} color={colors.textMuted} />
    </Tap>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: {
    flexDirection: "row", gap: 6, alignItems: "center", paddingHorizontal: 10, paddingVertical: 5,
    borderRadius: radius.pill, backgroundColor: colors.surfaceRaised,
  },
  chipLabel: { fontFamily, fontSize: 12.5, color: colors.textMuted, fontWeight: "600" },
  chipValue: { fontFamily, fontSize: 12.5, color: colors.mint, fontWeight: "800" },
  segment: {
    flexDirection: "row", padding: 4, gap: 4, borderRadius: radius.pill,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  segBtn: { flex: 1, minHeight: touchMin, borderRadius: radius.pill, alignItems: "center", justifyContent: "center" },
  segSel: { backgroundColor: colors.primary },
  segText: { fontFamily, fontSize: 15, fontWeight: "700", color: colors.textMuted },
  navRow: { flexDirection: "row", alignItems: "center", gap: space.md, paddingHorizontal: space.lg, minHeight: 60 },
  navDivider: { borderBottomWidth: 1, borderBottomColor: colors.border },
  navIcon: { width: 34, height: 34, borderRadius: 17, backgroundColor: colors.surfaceRaised, alignItems: "center", justifyContent: "center" },
});
