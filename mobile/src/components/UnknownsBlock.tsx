/**
 * Composant UnknownsBlock — « Ce que nous ne savons pas » : informations manquantes, limites, désaccords.
 * Replié par défaut (titre + nombre de points) pour ne pas noyer l'essentiel ; rien n'est affiché si la liste est vide.
 */
import { StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { useTx } from "../i18n/data";
import { colors, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { Collapsible } from "./ui";

export function UnknownsBlock({ items, title }: { items: string[]; title?: string }) {
  const t = useT();
  const tx = useTx();
  const unique = items.map(tx).filter((v, i, arr) => v && arr.indexOf(v) === i);
  if (unique.length === 0) return null;
  return (
    <Collapsible title={title ?? t.unknowns.title} summary={t.unknowns.count(unique.length)} icon="help" accent={colors.warn}>
      {unique.map((x) => (
        <View key={x} style={styles.row}>
          <View style={styles.bullet} />
          <Text style={[type.body, { flex: 1 }]}>{x}</Text>
        </View>
      ))}
    </Collapsible>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  bullet: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.warn, marginTop: 9 },
});

export default UnknownsBlock;
