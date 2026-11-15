/**
 * Composant ScoreRing — Score d'adéquation sur 100, dessiné comme un anneau dont l'arc est
 * exactement proportionnel au score (61 points = 61 % du cercle). Le chiffre est toujours écrit.
 */
import { useEffect, useRef, useState } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { fmtNum } from "../format";
import { alpha, colors } from "../theme/tokens";
import { fontFamily } from "../theme/typography";
import { settle } from "./ui";

export function ScoreRing({ score, size = 72, color = colors.mint, label }: { score: number; size?: number; color?: string; label?: string }) {
  const pct = Math.max(0, Math.min(100, score));
  const stroke = Math.max(5, size / 11);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  // Arc animé de 0 au score à l'affichage.
  const v = useRef(new Animated.Value(0)).current;
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = v.addListener(({ value }) => setShown(value));
    settle(Animated.timing(v, { toValue: pct, duration: 700, easing: Easing.out(Easing.cubic), useNativeDriver: false }),
      v, pct);
    return () => v.removeListener(id);
  }, [v, pct]);
  return (
    <View style={{ width: size, height: size }} accessible accessibilityLabel={label}>
      <Svg width={size} height={size}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={alpha(color, 0.16)} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={`${(shown / 100) * c} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View style={[StyleSheet.absoluteFill, styles.center]}>
        <Text style={[styles.value, { fontSize: size * 0.32 }]}>{fmtNum(pct, 0)}</Text>
        <Text style={[styles.unit, { fontSize: Math.max(9, size * 0.13) }]}>/100</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center" },
  value: { fontFamily, fontWeight: "800", color: colors.text, letterSpacing: -0.5, lineHeight: undefined },
  unit: { fontFamily, fontWeight: "700", color: colors.textMuted, marginTop: -2 },
});

export default ScoreRing;
