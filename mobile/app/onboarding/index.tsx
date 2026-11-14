/**
 * Écran : Bienvenue (simulation) puis choix d'un persona ou création d'un profil fictif.
 */
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { getPersonas } from "../../src/api/profiles";
import { Button, Card, ErrorState, Loading, Screen } from "../../src/components/ui";
import { fr } from "../../src/i18n/fr";
import { colors, radius, space } from "../../src/theme/tokens";
import { type } from "../../src/theme/typography";

export default function Bienvenue() {
  const personas = useQuery({ queryKey: ["personas"], queryFn: getPersonas });
  return (
    <Screen>
      <View style={{ gap: space.sm, marginTop: space.lg }}>
        <Text style={type.title}>{fr.appName}</Text>
        <Text style={type.h3}>{fr.subtitle}</Text>
        <Text style={type.body}>
          Choisissez un profil d'investisseur fictif. EasyTrade présente des pistes à explorer classées selon leur adéquation
          à ce profil, et explique chacune à partir de données publiques datées.
        </Text>
      </View>

      <Card style={{ backgroundColor: colors.surfaceMuted }}>
        <Text style={type.body}>
          ✓ Simulation uniquement : aucune transaction, aucun compte.{"\n"}✓ Profils fictifs : aucune donnée personnelle demandée.
          {"\n"}✓ Ceci n'est pas un conseil financier.
        </Text>
      </Card>

      <Text style={type.h2} accessibilityRole="header">Choisir un persona</Text>
      {personas.isLoading ? <Loading /> : null}
      {personas.error ? <ErrorState error={personas.error} onRetry={() => personas.refetch()} /> : null}
      {personas.data?.map((p) => {
        const h = p.profil.horizon_annees;
        return (
          <Pressable
            key={p.id}
            accessibilityRole="button"
            accessibilityLabel={`Choisir le profil ${p.profil.nom}`}
            onPress={() => router.push({ pathname: "/onboarding/resume", params: { id: p.id } })}
            style={({ pressed }) => [styles.persona, pressed && { opacity: 0.8 }]}
          >
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{p.profil.nom[0]}</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={type.h3}>
                {p.profil.nom}, {p.profil.age} ans
              </Text>
              <Text style={type.small}>
                Risque {p.profil.tolerance_risque} · horizon {h.max ? `${h.min} à ${h.max} ans` : `${h.min} ans et plus`}
              </Text>
              <Text style={type.body}>{p.profil.objectif}</Text>
            </View>
            <Text style={styles.chevron}>›</Text>
          </Pressable>
        );
      })}

      <Button label="Créer un profil fictif" variant="secondary" onPress={() => router.push("/onboarding/questionnaire")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  persona: {
    flexDirection: "row", alignItems: "center", gap: space.md, backgroundColor: colors.surface,
    borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: space.lg,
  },
  avatar: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  avatarText: { color: colors.primaryText, fontSize: 22, fontWeight: "700" },
  chevron: { fontSize: 28, color: colors.textMuted },
});
