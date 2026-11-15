/**
 * Briques d'interface communes : écran, carte, section, bouton, pastille, jauge de niveau,
 * zone tactile animée (`Tap`), apparition en fondu (`FadeIn`), section repliable (`Collapsible`),
 * états de chargement et d'erreur.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ActivityIndicator, Animated, Easing, Platform, Pressable, ScrollView, StyleSheet, Text, View,
  type GestureResponderEvent, type PressableProps, type StyleProp, type ViewStyle,
} from "react-native";
import { useT } from "../i18n";
import { useTx } from "../i18n/data";
import { alpha, colors, radius, space, touchMin } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import { Glow } from "./Glow";
import { Icon, type IconName } from "./Icon";

const NATIVE = Platform.OS !== "web";
const WEB = Platform.OS === "web";
const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/*
 * Animations sur le web : CSS (images clés et transitions), jamais `Animated` lié à un style. Avec
 * react-native-web, une vue animée re-rendue pendant l'animation garde la valeur du moment du re-rendu :
 * une carte restait à 92 % d'opacité, et une barre de risque aurait pu se figer à mi-longueur. Les
 * animations CSS sont exécutées par le navigateur et finissent toujours à leur valeur. Sur téléphone,
 * `Animated` avec le pilote natif reste utilisé.
 */
const EASE = "cubic-bezier(0.2, 0.7, 0.2, 1)";

/** Style web : entrée en fondu et léger glissement, après `delayMs`. */
export function webEnter(delayMs = 0, durationMs = 320): ViewStyle {
  return {
    animationKeyframes: [{ "0%": { opacity: 0, transform: [{ translateY: 10 }] }, "100%": { opacity: 1, transform: [{ translateY: 0 }] } }],
    animationDuration: `${durationMs}ms`,
    animationDelay: `${delayMs}ms`,
    animationTimingFunction: EASE,
    animationFillMode: "both",
  } as unknown as ViewStyle;
}

/** Style web : une barre qui pousse de 0 jusqu'à sa largeur finale (la largeur statique reste la référence). */
export function webGrow(width: string, durationMs = 650): ViewStyle {
  return {
    animationKeyframes: [{ "0%": { width: "0%" }, "100%": { width } }],
    animationDuration: `${durationMs}ms`,
    animationTimingFunction: EASE,
    animationFillMode: "both",
  } as unknown as ViewStyle;
}

/** Style web : transition douce des propriétés qui changent au toucher ou au survol. */
export const webTransition = {
  transitionProperty: "transform, opacity, background-color, border-color, box-shadow, width",
  transitionDuration: "180ms",
  transitionTimingFunction: EASE,
} as unknown as ViewStyle;

type TapState = { pressed: boolean; hovered: boolean };
type TapProps = Omit<PressableProps, "style" | "children"> & {
  style?: StyleProp<ViewStyle> | ((s: TapState) => StyleProp<ViewStyle>);
  children?: ReactNode;
  /** Échelle au toucher (0,96 par défaut ; 1 = sans rebond). */
  scaleTo?: number;
};

/**
 * Zone tactile avec retour visuel : léger enfoncement à ressort au toucher, éclaircissement au survol (web).
 * À utiliser à la place de `Pressable` pour tout élément cliquable.
 */
export function Tap({ style, children, scaleTo = 0.96, onPressIn, onPressOut, onHoverIn, onHoverOut, disabled, ...rest }: TapProps) {
  const scale = useRef(new Animated.Value(1)).current;
  const [state, setState] = useState<TapState>({ pressed: false, hovered: false });
  const spring = (to: number) => {
    if (!WEB) {
      settle(Animated.spring(scale, { toValue: to, useNativeDriver: NATIVE, speed: 40, bounciness: to === 1 ? 10 : 0 }),
        scale, to);
    }
  };
  const resolved = typeof style === "function" ? style(state) : style;
  if (WEB) {
    // Web : enfoncement et survol par style + transition CSS (voir l'en-tête de ce fichier).
    return (
      <Pressable
        {...rest}
        disabled={disabled}
        onPressIn={(e) => { setState((s) => ({ ...s, pressed: true })); onPressIn?.(e); }}
        onPressOut={(e) => { setState((s) => ({ ...s, pressed: false })); onPressOut?.(e); }}
        onHoverIn={(e) => { setState((s) => ({ ...s, hovered: true })); onHoverIn?.(e); }}
        onHoverOut={(e) => { setState((s) => ({ ...s, hovered: false })); onHoverOut?.(e); }}
        style={[resolved, webTransition, state.hovered && !disabled && styles.hover,
          { transform: [{ scale: state.pressed && !disabled ? scaleTo : 1 }] }]}
      >
        {children}
      </Pressable>
    );
  }
  return (
    <AnimatedPressable
      {...rest}
      disabled={disabled}
      onPressIn={(e: GestureResponderEvent) => { setState((s) => ({ ...s, pressed: true })); spring(scaleTo); onPressIn?.(e); }}
      onPressOut={(e: GestureResponderEvent) => { setState((s) => ({ ...s, pressed: false })); spring(1); onPressOut?.(e); }}
      onHoverIn={(e) => { setState((s) => ({ ...s, hovered: true })); onHoverIn?.(e); }}
      onHoverOut={(e) => { setState((s) => ({ ...s, hovered: false })); onHoverOut?.(e); }}
      style={[resolved, state.hovered && !disabled && styles.hover, { transform: [{ scale }] }]}
    >
      {children}
    </AnimatedPressable>
  );
}

/**
 * Lance une animation vers sa valeur finale et garantit cette valeur même si l'animation est interrompue.
 * Sur le web (react-native-web), une animation en cours peut être arrêtée quand la vue animée est re-rendue
 * (ex. rafraîchissement d'une requête) : sans ce garde-fou, une barre ou une carte resterait figée à mi-chemin.
 */
export function settle(animation: Animated.CompositeAnimation, value: Animated.Value, final: number): void {
  animation.start(({ finished }) => {
    if (!finished) value.setValue(final);
  });
}

/** Apparition en fondu et léger glissement ; `index` décale l'entrée des éléments d'une liste. */
export function FadeIn({ children, index = 0, style }: { children: ReactNode; index?: number; style?: StyleProp<ViewStyle> }) {
  const delay = Math.min(index, 8) * 55;
  const v = useRef(new Animated.Value(WEB ? 1 : 0)).current;
  useEffect(() => {
    if (WEB) return;
    settle(Animated.timing(v, {
      toValue: 1, duration: 320, delay, easing: Easing.out(Easing.cubic), useNativeDriver: NATIVE,
    }), v, 1);
  }, [v, delay]);
  if (WEB) return <View style={[style, webEnter(delay)]}>{children}</View>;
  const translateY = v.interpolate({ inputRange: [0, 1], outputRange: [10, 0] });
  return <Animated.View style={[style, { opacity: v, transform: [{ translateY }] }]}>{children}</Animated.View>;
}

/** Section repliable : un en-tête cliquable (titre, résumé, chevron qui pivote) et son contenu. */
export function Collapsible({ title, summary, children, initiallyOpen = false, icon, accent = colors.mint }: {
  title: string; summary?: string; children: ReactNode; initiallyOpen?: boolean; icon?: IconName; accent?: string;
}) {
  const [open, setOpen] = useState(initiallyOpen);
  const rot = useRef(new Animated.Value(initiallyOpen ? 1 : 0)).current;
  const toggle = () => {
    if (!WEB) settle(Animated.timing(rot, { toValue: open ? 0 : 1, duration: 200, useNativeDriver: NATIVE }), rot, open ? 0 : 1);
    setOpen(!open);
  };
  const rotate = WEB ? (open ? "180deg" : "0deg") : rot.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "180deg"] });
  return (
    <View style={styles.collapse}>
      <Tap onPress={toggle} scaleTo={0.985} accessibilityRole="button" accessibilityState={{ expanded: open }}
        style={styles.collapseHead}>
        {icon ? (
          <View style={[styles.collapseIcon, { backgroundColor: alpha(accent, 0.12) }]}>
            <Icon name={icon} size={18} color={accent} />
          </View>
        ) : null}
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={type.h3} accessibilityRole="header">{title}</Text>
          {summary ? <Text style={type.small} numberOfLines={open ? undefined : 1}>{summary}</Text> : null}
        </View>
        {WEB ? (
          <View style={[{ transform: [{ rotate: rotate as string }] }, webTransition]}>
            <Icon name="chevronDown" size={20} color={colors.mint} />
          </View>
        ) : (
          <Animated.View style={{ transform: [{ rotate }] }}>
            <Icon name="chevronDown" size={20} color={colors.mint} />
          </Animated.View>
        )}
      </Tap>
      {open ? <FadeIn style={styles.collapseBody}>{children}</FadeIn> : null}
    </View>
  );
}

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
    <Tap
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
        pressed && !disabled && (variant === "primary" ? styles.btnPrimaryPressed : styles.btnPressed),
        disabled && { opacity: 0.4 },
      ]}
    >
      {icon ? <Icon name={icon} size={18} color={fg} /> : null}
      <Text style={[styles.btnText, { color: fg }]}>{label}</Text>
    </Tap>
  );
}

/** Lien textuel avec flèche (navigation secondaire). */
export function LinkText({ label, onPress, icon = "arrowRight", a11yRole = "link" }: {
  label: string; onPress: () => void; icon?: IconName | null; a11yRole?: "link" | "button";
}) {
  return (
    <Tap onPress={onPress} accessibilityRole={a11yRole} hitSlop={10} style={({ pressed }) => [styles.link, pressed && { opacity: 0.7 }]}>
      <Text style={styles.linkText}>{label}</Text>
      {icon ? <Icon name={icon} size={16} color={colors.link} /> : null}
    </Tap>
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
  const tx = useTx();
  const message = tx(error instanceof Error ? error.message : String(error));
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
  btnPressed: { backgroundColor: alpha(colors.mint, 0.1) },
  btnPrimaryPressed: { backgroundColor: colors.mint, shadowOpacity: 0.6 },
  hover: { opacity: 0.92 },
  collapse: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  collapseHead: { flexDirection: "row", alignItems: "center", gap: space.md, padding: space.lg, minHeight: touchMin + 12 },
  collapseIcon: { width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center" },
  collapseBody: { paddingHorizontal: space.lg, paddingBottom: space.lg, gap: space.md },
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
