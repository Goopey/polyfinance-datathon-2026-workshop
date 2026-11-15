/**
 * Composant PaletteStack — Signature visuelle de l'accueil : six capsules empilées du vert profond à la menthe
 * (la palette de l'application), chacune portant une étape du parcours, jusqu'à « Vos pistes ».
 */
import { StyleSheet, Text, View } from "react-native";
import { palette } from "../theme/tokens";
import { fontFamily } from "../theme/typography";

const SHADES = [palette.g900, palette.g800, palette.g700, palette.g600, palette.g300, palette.g100];

export function PaletteStack({ labels }: { labels: string[] }) {
  return (
    <View style={styles.wrap} accessibilityLabel={labels.join(" → ")}>
      {SHADES.map((bg, i) => {
        const last = i === SHADES.length - 1;
        const light = i >= 4;
        return (
          <View
            key={bg}
            style={[
              styles.capsule,
              { backgroundColor: bg, zIndex: i, marginTop: i === 0 ? 0 : -22 },
              last && styles.last,
              i === 0 && { borderColor: "rgba(218,241,222,0.10)" },
            ]}
          >
            <Text style={[styles.text, { color: light ? palette.g900 : palette.g100 }, last && styles.lastText]}>
              {`0${i + 1}`}  {labels[i]}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: "100%", maxWidth: 340, alignSelf: "center", paddingVertical: 8 },
  capsule: {
    height: 58, borderRadius: 29, paddingHorizontal: 22, paddingTop: 10,
    borderWidth: 1, borderColor: "rgba(218,241,222,0.08)",
    shadowColor: "#000", shadowOpacity: 0.45, shadowRadius: 14, shadowOffset: { width: 0, height: 8 }, elevation: 6,
  },
  last: { height: 92, borderRadius: 46, paddingTop: 16, justifyContent: "flex-start" },
  text: { fontFamily, fontSize: 11.5, fontWeight: "600", letterSpacing: 1, textTransform: "uppercase", opacity: 0.9 },
  lastText: { fontSize: 17, fontWeight: "800", letterSpacing: -0.2, textTransform: "none", opacity: 1 },
});

export default PaletteStack;
