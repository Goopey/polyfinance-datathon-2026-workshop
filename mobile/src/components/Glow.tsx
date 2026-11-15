/**
 * Composant Glow — Halo lumineux en haut d'écran (rappel de la palette : un faisceau menthe sur vert profond).
 * Purement décoratif, sans interaction.
 */
import { StyleSheet, View } from "react-native";
import Svg, { Defs, RadialGradient, Rect, Stop } from "react-native-svg";
import { palette } from "../theme/tokens";

export function Glow({ height = 460 }: { height?: number }) {
  return (
    <View pointerEvents="none" style={[styles.wrap, { height }]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Svg width="100%" height="100%">
        <Defs>
          <RadialGradient id="beam" cx="12%" cy="0%" rx="85%" ry="75%" fx="12%" fy="0%">
            <Stop offset="0" stopColor={palette.g100} stopOpacity="0.22" />
            <Stop offset="0.35" stopColor={palette.g300} stopOpacity="0.10" />
            <Stop offset="1" stopColor={palette.g900} stopOpacity="0" />
          </RadialGradient>
          <RadialGradient id="ember" cx="100%" cy="35%" rx="55%" ry="45%">
            <Stop offset="0" stopColor={palette.g600} stopOpacity="0.35" />
            <Stop offset="1" stopColor={palette.g900} stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Rect x="0" y="0" width="100%" height="100%" fill="url(#ember)" />
        <Rect x="0" y="0" width="100%" height="100%" fill="url(#beam)" />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: "absolute", top: 0, left: 0, right: 0 },
});

export default Glow;
