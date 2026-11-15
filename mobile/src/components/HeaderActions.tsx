/**
 * Composant HeaderActions — Coin supérieur droit de chaque écran : sélecteur de langue FR / EN
 * (et, en mode développement seulement, une pastille « Démo »).
 */
import { StyleSheet, Text, View } from "react-native";
import { USE_MOCKS } from "../api/client";
import { Tap } from "./ui";
import { useT } from "../i18n";
import { useSettings, type Lang } from "../store/settings";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily } from "../theme/typography";

export function LangToggle() {
  const t = useT();
  const { lang, setLang } = useSettings();
  return (
    <View style={styles.seg} accessibilityRole="radiogroup" accessibilityLabel={t.lang.label}>
      {(["fr", "en"] as Lang[]).map((l) => {
        const on = lang === l;
        return (
          <Tap
            key={l}
            onPress={() => setLang(l)}
            accessibilityRole="radio"
            accessibilityState={{ checked: on }}
            accessibilityLabel={t.lang[l]}
            hitSlop={6}
            scaleTo={0.88}
            style={({ hovered }) => [styles.opt, on && styles.optOn, hovered && !on && { backgroundColor: alpha(colors.mint, 0.08) }]}
          >
            <Text style={[styles.optText, on && styles.optTextOn]}>{l.toUpperCase()}</Text>
          </Tap>
        );
      })}
    </View>
  );
}

export function HeaderActions() {
  const t = useT();
  return (
    <View style={styles.row}>
      {USE_MOCKS ? (
        <View style={styles.demo} accessibilityLabel={t.demo.long}>
          <Text style={styles.demoText}>{t.demo.chip}</Text>
        </View>
      ) : null}
      <LangToggle />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: space.sm, marginRight: space.md },
  seg: {
    flexDirection: "row", padding: 3, borderRadius: radius.pill,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  opt: { minWidth: 40, height: 30, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", paddingHorizontal: 10 },
  optOn: { backgroundColor: colors.mint },
  optText: { fontFamily, fontSize: 12.5, fontWeight: "700", letterSpacing: 0.6, color: colors.textMuted },
  optTextOn: { color: colors.primaryText },
  demo: {
    paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill,
    backgroundColor: alpha(colors.gold, 0.14), borderWidth: 1, borderColor: alpha(colors.gold, 0.4),
  },
  demoText: { fontFamily, fontSize: 11, fontWeight: "700", color: colors.gold, letterSpacing: 0.4 },
});

export default HeaderActions;
