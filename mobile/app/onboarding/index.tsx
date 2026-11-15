/**
 * Écran : Bienvenue — « Choisissez votre profil d'investisseur » : profils prêts à l'emploi ou questionnaire.
 */
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { getPersonas } from "../../src/api/profiles";
import { HeaderActions } from "../../src/components/HeaderActions";
import { Icon } from "../../src/components/Icon";
import { PaletteStack } from "../../src/components/PaletteStack";
import { ErrorState, Loading, Screen } from "../../src/components/ui";
import { useT } from "../../src/i18n";
import { alpha, colors, palette, radius, space } from "../../src/theme/tokens";
import { fontFamily, type } from "../../src/theme/typography";
import type { Persona } from "../../src/types/contracts";

/** Une teinte de la palette par persona, pour l'avatar. */
const AVATAR = [palette.g300, palette.g100, "#B5D8C0", palette.g600];
const RISK_COLOR: Record<string, string> = { "élevé": colors.bad, "élevée": colors.bad, "modéré": colors.warn, "modérée": colors.warn, faible: colors.good };

export default function Bienvenue() {
  const t = useT();
  const insets = useSafeAreaInsets();
  const personas = useQuery({ queryKey: ["personas"], queryFn: getPersonas });
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={[styles.topBar, { paddingTop: insets.top + space.sm }]}>
        <View style={styles.brand}>
          <View style={styles.brandMark} />
          <Text style={styles.brandText}>{t.appName}</Text>
        </View>
        <HeaderActions />
      </View>
      <Screen>
        <View style={styles.hero}>
          <View style={{ gap: space.sm }}>
            <Text style={type.eyebrow}>{t.welcome.eyebrow}</Text>
            <Text style={type.display} accessibilityRole="header">{t.welcome.title}</Text>
            <Text style={[type.body, { color: colors.textMuted }]}>{t.welcome.body}</Text>
          </View>
          <PaletteStack labels={t.welcome.stack} />
        </View>

        <Text style={type.h2} accessibilityRole="header">{t.welcome.personasTitle}</Text>
        {personas.isLoading ? <Loading /> : null}
        {personas.error ? <ErrorState error={personas.error} onRetry={() => personas.refetch()} /> : null}
        <View style={{ gap: space.md }}>
          {personas.data?.map((p, i) => <PersonaCard key={p.id} p={p} tint={AVATAR[i % AVATAR.length]} />)}
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => router.push("/onboarding/questionnaire")}
          style={({ pressed }) => [styles.custom, pressed && { opacity: 0.85 }]}
        >
          <View style={styles.customIcon}>
            <Icon name="sliders" size={20} color={colors.primaryText} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={type.h3}>{t.welcome.custom}</Text>
            <Text style={type.small}>{t.welcome.customHint}</Text>
          </View>
          <Icon name="arrowRight" size={20} color={colors.mint} />
        </Pressable>
      </Screen>
    </View>
  );
}

function PersonaCard({ p, tint }: { p: Persona; tint: string }) {
  const t = useT();
  const h = p.profil.horizon_annees;
  const risk = p.profil.tolerance_risque;
  const riskColor = RISK_COLOR[risk] ?? colors.info;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={t.welcome.choose(p.profil.nom)}
      onPress={() => router.push({ pathname: "/onboarding/resume", params: { id: p.id } })}
      style={({ pressed }) => [styles.persona, pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] }]}
    >
      <View style={[styles.avatar, { backgroundColor: tint }]}>
        <Text style={styles.avatarText}>{p.profil.nom[0]}</Text>
      </View>
      <View style={{ flex: 1, gap: 6 }}>
        <Text style={type.h3}>{t.welcome.nameAge(p.profil.nom, p.profil.age)}</Text>
        <View style={styles.tags}>
          <View style={[styles.tag, { backgroundColor: alpha(riskColor, 0.12), borderColor: alpha(riskColor, 0.35) }]}>
            <Text style={[styles.tagText, { color: riskColor }]}>{t.welcome.risk(t.riskLevel[risk] ?? risk)}</Text>
          </View>
          <View style={[styles.tag, { backgroundColor: colors.infoBg, borderColor: alpha(colors.info, 0.35) }]}>
            <Text style={[styles.tagText, { color: colors.info }]}>{t.welcome.horizon(h.min, h.max)}</Text>
          </View>
        </View>
        <Text style={[type.small, { color: colors.text }]}>{p.profil.objectif}</Text>
      </View>
      <Icon name="chevronRight" size={22} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  topBar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: space.lg, paddingBottom: space.sm, backgroundColor: colors.bg, zIndex: 2,
  },
  brand: { flexDirection: "row", alignItems: "center", gap: space.sm },
  brandMark: { width: 22, height: 12, borderRadius: 6, backgroundColor: colors.mint },
  brandText: { fontFamily, fontSize: 18, fontWeight: "800", color: colors.text, letterSpacing: -0.3 },
  hero: { gap: space.xl, marginTop: space.md, marginBottom: space.sm },
  persona: {
    flexDirection: "row", alignItems: "center", gap: space.md, backgroundColor: colors.surface,
    borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: space.lg,
  },
  avatar: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily, color: colors.primaryText, fontSize: 22, fontWeight: "800" },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  tag: { borderRadius: radius.pill, borderWidth: 1, paddingHorizontal: 9, paddingVertical: 2 },
  tagText: { fontFamily, fontSize: 12.5, fontWeight: "700" },
  custom: {
    flexDirection: "row", alignItems: "center", gap: space.md, padding: space.lg, borderRadius: radius.lg,
    borderWidth: 1.5, borderStyle: "dashed", borderColor: colors.borderStrong, backgroundColor: alpha(colors.mint, 0.04),
  },
  customIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
});
