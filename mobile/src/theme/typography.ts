/**
 * Typographie : tailles confortables pour une lecture sans effort. Conception : docs/07_UX_UI.md
 */
import { StyleSheet } from "react-native";
import { colors } from "./tokens";

export const type = StyleSheet.create({
  title: { fontSize: 26, fontWeight: "700", color: colors.text, lineHeight: 32 },
  h2: { fontSize: 20, fontWeight: "700", color: colors.text, lineHeight: 26 },
  h3: { fontSize: 17, fontWeight: "600", color: colors.text, lineHeight: 23 },
  body: { fontSize: 16, color: colors.text, lineHeight: 23 },
  small: { fontSize: 14, color: colors.textMuted, lineHeight: 20 },
  caption: { fontSize: 12, color: colors.textMuted, lineHeight: 16 },
  label: { fontSize: 14, fontWeight: "600", color: colors.text },
});
