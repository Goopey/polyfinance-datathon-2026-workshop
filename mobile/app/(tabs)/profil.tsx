/**
 * Écran : Profil courant, mode Simple / Avancé, changement de profil, accès aux écrans annexes.
 */
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { API_URL, USE_MOCKS } from "../../src/api/client";
import { getProfile } from "../../src/api/profiles";
import { Button, Card, Row, Screen, Section } from "../../src/components/ui";
import { fmtWeight } from "../../src/format";
import { fr } from "../../src/i18n/fr";
import { useProfileStore } from "../../src/store/profile";
import { useSettings, type ReadingMode } from "../../src/store/settings";
import { colors, radius, space, touchMin } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";
import { CRITERIA } from "../../src/types/contracts";

export default function Profil() {
  const { profileId, summary, reset } = useProfileStore();
  const { mode, setMode } = useSettings();
  const profile = useQuery({ queryKey: ["profile", profileId], queryFn: () => getProfile(profileId!), enabled: !!profileId });

  return (
    <Screen>
      <Section title="Profil fictif courant">
        <Card>
          <Text style={type.h3}>{summary ?? "Aucun profil"}</Text>
          {profile.data ? (
            <Text style={type.small}>
              Poids : {CRITERIA.map((k) => `${fr.criteria[k]} ${fmtWeight(profile.data.weights[k])}`).join(" · ")}
            </Text>
          ) : null}
          <Row>
            {profileId ? (
              <Button label="Voir les poids et règles" variant="secondary"
                onPress={() => router.push({ pathname: "/onboarding/resume", params: { id: profileId } })} />
            ) : null}
            <Button label="Changer de profil" variant="secondary" onPress={() => { reset(); router.replace("/onboarding"); }} />
          </Row>
        </Card>
      </Section>

      <Section title="Niveau de lecture">
        <View style={styles.segment} accessibilityRole="radiogroup">
          {(["simple", "avance"] as ReadingMode[]).map((m) => (
            <Pressable key={m} onPress={() => setMode(m)} accessibilityRole="radio" accessibilityState={{ checked: mode === m }}
              style={[styles.segBtn, mode === m && styles.segSel]}>
              <Text style={[type.label, mode === m && { color: colors.primaryText }]}>
                {mode === m ? "◉ " : "○ "}{m === "simple" ? "Simple" : "Avancé"}
              </Text>
            </Pressable>
          ))}
        </View>
        <Text style={type.small}>
          Simple : l'essentiel, sans jargon. Avancé : tous les indicateurs, les arguments complets du débat et les identifiants des preuves.
        </Text>
      </Section>

      <Section title="Aller plus loin">
        <Button label="Comparer deux profils" variant="secondary" onPress={() => router.push("/comparer")} />
        <Button label="Données et sources" variant="secondary" onPress={() => router.push("/donnees")} />
      </Section>

      <Card style={{ backgroundColor: colors.surfaceMuted }}>
        <Text style={type.h3}>À propos</Text>
        <Text style={type.body}>
          {fr.appName} est un simulateur d'aide à la décision. Il ne passe aucun ordre, ne relie aucun compte et ne fournit pas de conseil
          financier personnalisé. Les profils sont fictifs ; les indicateurs décrivent le passé et ne prédisent rien.
        </Text>
        <Text style={type.caption}>
          Source des données : {USE_MOCKS ? "données entièrement fictives (mode développement)" : `API ${API_URL}`}
        </Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  segment: { flexDirection: "row", gap: space.sm },
  segBtn: {
    flex: 1, minHeight: touchMin, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.primary,
    alignItems: "center", justifyContent: "center", backgroundColor: colors.surface,
  },
  segSel: { backgroundColor: colors.primary },
});
