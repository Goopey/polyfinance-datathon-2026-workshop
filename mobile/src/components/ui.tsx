/**
 * Briques d'interface communes : écran, carte, section, bouton, pastille, jauge de niveau,
 * états de chargement et d'erreur.
 */
import type { ReactNode } from "react";
import {
  ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type StyleProp, type ViewStyle,
} from "react-native";
import { useT } from "../i18n";
import { alpha, colors, radius, space, touchMin } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import { Glow } from "./Glow";
import { Icon, type IconName } from "./Icon";

export function Screen({ children, scroll = true, glow = true }: { children: ReactNode; scroll?: boolean; glow?: boolean }) {
  if (!scroll) return <View style={[styles.screen, styles.pad]}>{glow ? <Glow /> : null}{children}</View>;
  return (
    <View style={styles.screen}>
      {glow ? <Glow /> : null}
      <ScrollView style={styles.scroll} contentContainerStyle={[styles.pad, styles.scrollPad]}>
        <View style={styles.maxWidth}>{children}</View>
      </ScrollView>
    </View>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Section({ title, children, right, hint }: { title: string; children: ReactNode; right?: ReactNode; hint?: string }) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={type.h2} accessibilityRole="header">{title}</Text>
          {hint ? <Text style={type.small}>{hint}</Text> : null}
        </View>
        {right}
      </View>
      {children}
    </View>
  );
}

export function Button({
  label, onPress, variant = "primary", disabled, accessibilityHint, icon,
}: {
  label: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost";
  disabled?: boolean;
  accessibilityHint?: string;
  icon?: IconName;
}) {
  const fg = variant === "primary" ? colors.primaryText : colors.mint;
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
        pressed && !disabled && { opacity: 0.82, transform: [{ scale: 0.985 }] },
        disabled && { opacity: 0.4 },
      ]}
    >
      {icon ? <Icon name={icon} size={18} color={fg} /> : null}
      <Text style={[styles.btnText, { color: fg }]}>{label}</Text>
    </Pressable>
  );
}

/** Lien textuel avec flèche (navigation secondaire). */
export function LinkText({ label, onPress, icon = "arrowRight", a11yRole = "link" }: {
  label: string; onPress: () => void; icon?: IconName | null; a11yRole?: "link" | "button";
}) {
  return (
    <Pressable onPress={onPress} accessibilityRole={a11yRole} hitSlop={10} style={({ pressed }) => [styles.link, pressed && { opacity: 0.7 }]}>
      <Text style={styles.linkText}>{label}</Text>
      {icon ? <Icon name={icon} size={16} color={colors.link} /> : null}
    </Pressable>
  );
}

/** Pastille d'état : texte + couleur + élément de tête (icône ou jauge), jamais la couleur seule. */
export function Pill({ text, fg, bg, icon, leading }: { text: string; fg: string; bg: string; icon?: IconName | string; leading?: ReactNode }) {
  return (
    <View style={[styles.pill, { backgroundColor: bg, borderColor: alpha(fg.startsWith("#") ? fg : "#DAF1DE", 0.32) }]}>
      {leading}
      {icon && !leading ? (
        isIconName(icon) ? <Icon name={icon} size={14} color={fg} strokeWidth={2.4} /> : <Text style={[styles.pillText, { color: fg }]}>{icon}</Text>
      ) : null}
      <Text style={[styles.pillText, { color: fg }]}>{text}</Text>
    </View>
  );
}

function isIconName(s: string): s is IconName {
  return /^[a-z][A-Za-z]+$/.test(s);
}

/** Jauge en trois crans (niveau élevé / moyen / faible), lisible sans la couleur. */
export function LevelMeter({ level, color, shape = "dot" }: { level: 1 | 2 | 3; color: string; shape?: "dot" | "bar" }) {
  return (
    <View style={styles.meter} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {[1, 2, 3].map((n) => (
        <View
          key={n}
          style={[
            shape === "dot" ? styles.dot : [styles.bar, { height: 5 + n * 3 }],
            { backgroundColor: n <= level ? color : alpha(color, 0.22) },
          ]}
        />
      ))}
    </View>
  );
}

export function Loading({ label }: { label?: string }) {
  const t = useT();
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.mint} />
      <Text style={[type.small, { marginTop: space.sm }]}>{label ?? t.common.loading}</Text>
    </View>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useT();
  const message = error instanceof Error ? error.message : String(error);
  return (
    <Card style={{ borderColor: alpha(colors.bad, 0.45), backgroundColor: colors.badBg }}>
      <Row>
        <Icon name="x" size={18} color={colors.bad} strokeWidth={2.6} />
        <Text style={[type.h3, { color: colors.bad }]}>{t.common.errorTitle}</Text>
      </Row>
      <Text style={[type.body, { marginVertical: space.sm }]}>{message}</Text>
      {onRetry ? <Button label={t.common.retry} variant="secondary" icon="refresh" onPress={onRetry} /> : null}
    </Card>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  scroll: { flex: 1, backgroundColor: "transparent" },
  pad: { padding: space.lg },
  scrollPad: { paddingBottom: 112 },
  maxWidth: { width: "100%", maxWidth: 720, alignSelf: "center", gap: space.lg },
  card: {
    backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.lg,
    borderWidth: 1, borderColor: colors.border, gap: space.sm,
  },
  section: { gap: space.md, marginTop: space.sm },
  sectionHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: space.md },
  btn: {
    minHeight: touchMin + 4, paddingHorizontal: space.xl, borderRadius: radius.pill,
    alignItems: "center", justifyContent: "center", flexDirection: "row", gap: space.sm,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
    shadowColor: colors.primary, shadowOpacity: 0.35, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 4,
  },
  btnSecondary: { backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: colors.borderStrong },
  btnGhost: { backgroundColor: "transparent" },
  btnText: { fontFamily, fontSize: 16, fontWeight: "700" },
  link: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 32, alignSelf: "flex-start" },
  linkText: { fontFamily, color: colors.link, fontWeight: "700", fontSize: 15 },
  pill: {
    flexDirection: "row", alignItems: "center", gap: 6, borderRadius: radius.pill, borderWidth: 1,
    paddingHorizontal: 10, paddingVertical: 4, alignSelf: "flex-start",
  },
  pillText: { fontFamily, fontSize: 13, fontWeight: "700" },
  meter: { flexDirection: "row", alignItems: "flex-end", gap: 3 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  bar: { width: 4, borderRadius: 2 },
  center: { alignItems: "center", justifyContent: "center", padding: space.xl },
  row: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: space.sm },
});
