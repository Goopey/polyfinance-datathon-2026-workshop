/**
 * Composant UnknownsBlock — Bloc systématique « Ce que nous ne savons pas » : informations manquantes, limites, désaccords.
 */
import { StyleSheet, Text, View } from "react-native";
import { fr } from "../i18n/fr";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";

export function UnknownsBlock({ items, title = fr.unknownsTitle }: { items: string[]; title?: string }) {
  const unique = items.filter((v, i, arr) => arr.indexOf(v) === i);
  return (
    <View style={styles.box}>
      <Text style={type.h3} accessibilityRole="header">? {title}</Text>
      {unique.length === 0 ? (
        <Text style={type.body}>Aucune information manquante signalée pour cette analyse.</Text>
      ) : (
        unique.map((t) => (
          <View key={t} style={styles.row}>
            <Text style={styles.bullet}>?</Text>
            <Text style={[type.body, { flex: 1 }]}>{t}</Text>
          </View>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    backgroundColor: colors.warnBg, borderRadius: radius.lg, padding: space.lg, gap: space.sm,
    borderWidth: 1, borderColor: "#EBD49B",
  },
  row: { flexDirection: "row", gap: space.sm },
  bullet: { fontWeight: "700", color: colors.warn, width: 14 },
});

export default UnknownsBlock;
