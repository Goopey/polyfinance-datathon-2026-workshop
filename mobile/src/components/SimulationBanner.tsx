/**
 * Composant SimulationBanner — Bandeau permanent « Simulation — aucune transaction réelle ».
 * Affiché par la mise en page racine, donc sur tous les écrans (docs/08_CONFORMITE.md).
 * En mode données fictives, une seconde ligne le signale.
 */
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { USE_MOCKS } from "../api/client";
import { fr } from "../i18n/fr";
import { colors, space } from "../theme/tokens";

export function SimulationBanner() {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.wrap, { paddingTop: insets.top + space.xs }]} accessibilityRole="summary">
      <Text style={styles.text}>{fr.banner}</Text>
      {USE_MOCKS ? <Text style={styles.mock}>⚠ {fr.mockBanner}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: colors.banner, paddingHorizontal: space.lg, paddingBottom: space.xs },
  text: { color: colors.bannerText, fontSize: 12, fontWeight: "600", textAlign: "center" },
  mock: { color: "#FFD27A", fontSize: 11, textAlign: "center", marginTop: 2 },
});

export default SimulationBanner;
