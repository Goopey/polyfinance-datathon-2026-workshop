/**
 * Composant UnknownsBlock — Bloc systématique « Ce que nous ne savons pas » : informations manquantes, limites, désaccords.
 */
import { StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { Icon } from "./Icon";

export function UnknownsBlock({ items, title }: { items: string[]; title?: string }) {
  const t = useT();
  const unique = items.filter((v, i, arr) => arr.indexOf(v) === i);
  return (
    <View style={styles.box}>
      <View style={styles.head}>
        <Icon name="help" size={20} color={colors.warn} />
        <Text style={[type.h3, { color: colors.warn }]} accessibilityRole="header">{title ?? t.unknowns.title}</Text>
      </View>
      {unique.length === 0 ? (
        <Text style={type.body}>{t.unknowns.none}</Text>
      ) : (
        unique.map((x) => (
          <View key={x} style={styles.row}>
            <View style={styles.bullet} />
            <Text style={[type.body, { flex: 1 }]}>{x}</Text>
          </View>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    backgroundColor: alpha(colors.warn, 0.07), borderRadius: radius.lg, padding: space.lg, gap: space.sm,
    borderWidth: 1, borderColor: alpha(colors.warn, 0.28),
  },
  head: { flexDirection: "row", alignItems: "center", gap: space.sm },
  row: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  bullet: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.warn, marginTop: 9 },
});

export default UnknownsBlock;
