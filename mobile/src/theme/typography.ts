/**
 * Typographie : Inter sur le web (chargée par la mise en page racine), police système ailleurs.
 * Tailles confortables, hiérarchie nette. Conception : docs/07_UX_UI.md
 */
import { Platform, StyleSheet } from "react-native";
import { colors } from "./tokens";

export const fontFamily = Platform.select({
  web: "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  default: undefined,
});

export const type = StyleSheet.create({
  display: { fontFamily, fontSize: 34, fontWeight: "800", color: colors.text, lineHeight: 40, letterSpacing: -0.8 },
  title: { fontFamily, fontSize: 26, fontWeight: "800", color: colors.text, lineHeight: 32, letterSpacing: -0.4 },
  h2: { fontFamily, fontSize: 20, fontWeight: "700", color: colors.text, lineHeight: 26, letterSpacing: -0.2 },
  h3: { fontFamily, fontSize: 17, fontWeight: "600", color: colors.text, lineHeight: 23 },
  body: { fontFamily, fontSize: 16, color: colors.text, lineHeight: 24 },
  small: { fontFamily, fontSize: 14, color: colors.textMuted, lineHeight: 20 },
  caption: { fontFamily, fontSize: 12.5, color: colors.textMuted, lineHeight: 17 },
  label: { fontFamily, fontSize: 14, fontWeight: "600", color: colors.text },
  eyebrow: { fontFamily, fontSize: 12, fontWeight: "700", color: colors.textMuted, letterSpacing: 1.4, textTransform: "uppercase" },
});
