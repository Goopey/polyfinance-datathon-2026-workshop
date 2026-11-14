/**
 * Briques d'interface communes : écran, carte, section, bouton, états de chargement et d'erreur.
 */
import type { ReactNode } from "react";
import {
  ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type StyleProp, type ViewStyle,
} from "react-native";
import { colors, radius, space, touchMin } from "../theme/tokens";
import { type } from "../theme/typography";

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  if (!scroll) return <View style={[styles.screen, styles.pad]}>{children}</View>;
  return (
    <ScrollView style={styles.screen} contentContainerStyle={[styles.pad, styles.scrollPad]}>
      <View style={styles.maxWidth}>{children}</View>
    </ScrollView>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Section({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}>
        <Text style={type.h2} accessibilityRole="header">{title}</Text>
        {right}
      </View>
      {children}
    </View>
  );
}

export function Button({
  label, onPress, variant = "primary", disabled, accessibilityHint,
}: {
  label: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost";
  disabled?: boolean;
  accessibilityHint?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [
        styles.btn,
        variant === "primary" && styles.btnPrimary,
        variant === "secondary" && styles.btnSecondary,
        variant === "ghost" && styles.btnGhost,
        (pressed || disabled) && { opacity: disabled ? 0.45 : 0.8 },
      ]}
    >
      <Text style={[styles.btnText, variant === "primary" ? { color: colors.primaryText } : { color: colors.primary }]}>
        {label}
      </Text>
    </Pressable>
  );
}

export function Pill({ text, fg, bg, icon }: { text: string; fg: string; bg: string; icon?: string }) {
  return (
    <View style={[styles.pill, { backgroundColor: bg }]}>
      <Text style={[styles.pillText, { color: fg }]}>
        {icon ? `${icon} ` : ""}
        {text}
      </Text>
    </View>
  );
}

export function Loading({ label = "Chargement…" }: { label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} />
      <Text style={[type.small, { marginTop: space.sm }]}>{label}</Text>
    </View>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <Card style={{ borderColor: colors.bad }}>
      <Text style={type.h3}>✕ Une étape n'a pas abouti</Text>
      <Text style={[type.body, { marginVertical: space.sm }]}>{message}</Text>
      {onRetry ? <Button label="Réessayer" variant="secondary" onPress={onRetry} /> : null}
    </Card>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  pad: { padding: space.lg },
  scrollPad: { paddingBottom: 96 },
  maxWidth: { width: "100%", maxWidth: 720, alignSelf: "center", gap: space.lg },
  card: {
    backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.lg,
    borderWidth: 1, borderColor: colors.border, gap: space.sm,
  },
  section: { gap: space.md },
  sectionHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  btn: {
    minHeight: touchMin, paddingHorizontal: space.lg, borderRadius: radius.md,
    alignItems: "center", justifyContent: "center",
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnSecondary: { backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.primary },
  btnGhost: { backgroundColor: "transparent" },
  btnText: { fontSize: 16, fontWeight: "600" },
  pill: { borderRadius: radius.pill, paddingHorizontal: space.md, paddingVertical: 4, alignSelf: "flex-start" },
  pillText: { fontSize: 13, fontWeight: "600" },
  center: { alignItems: "center", justifyContent: "center", padding: space.xl },
  row: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: space.sm },
});
