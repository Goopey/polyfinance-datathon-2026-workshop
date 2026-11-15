/**
 * Composant Icon — Icônes vectorielles au trait (style Lucide, 24×24), à la place des émojis et glyphes.
 * Décoratives par défaut : le libellé voisin porte le sens.
 */
import Svg, { Circle, Ellipse, Path } from "react-native-svg";

type Shape = { d: string } | { c: [number, number, number] } | { e: [number, number, number, number] };

const ICONS = {
  compass: [{ c: [12, 12, 10] }, { d: "m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z" }],
  flask: [
    { d: "M10 2v7.53a2 2 0 0 1-.21.9L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.07-10.12A2 2 0 0 1 14 9.53V2" },
    { d: "M8.5 2h7" },
    { d: "M7 16h10" },
  ],
  user: [{ d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" }, { c: [12, 7, 4] }],
  globe: [{ c: [12, 12, 10] }, { d: "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" }, { d: "M2 12h20" }],
  search: [{ c: [11, 11, 8] }, { d: "m21 21-4.3-4.3" }],
  chevronRight: [{ d: "m9 18 6-6-6-6" }],
  chevronDown: [{ d: "m6 9 6 6 6-6" }],
  chevronUp: [{ d: "m18 15-6-6-6 6" }],
  arrowRight: [{ d: "M5 12h14" }, { d: "m12 5 7 7-7 7" }],
  info: [{ c: [12, 12, 10] }, { d: "M12 16v-4" }, { d: "M12 8h.01" }],
  help: [{ c: [12, 12, 10] }, { d: "M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" }, { d: "M12 17h.01" }],
  layers: [{ d: "M12 2 2 7l10 5 10-5-10-5z" }, { d: "m2 17 10 5 10-5" }, { d: "m2 12 10 5 10-5" }],
  database: [{ e: [12, 5, 9, 3] }, { d: "M3 5v14a9 3 0 0 0 18 0V5" }, { d: "M3 12a9 3 0 0 0 18 0" }],
  activity: [{ d: "M22 12h-4l-3 9L9 3l-3 9H2" }],
  refresh: [
    { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }, { d: "M21 3v5h-5" },
    { d: "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" }, { d: "M8 16H3v5" },
  ],
  check: [{ d: "M20 6 9 17l-5-5" }],
  x: [{ d: "M18 6 6 18" }, { d: "m6 6 12 12" }],
  plus: [{ d: "M5 12h14" }, { d: "M12 5v14" }],
  minus: [{ d: "M5 12h14" }],
  scale: [
    { d: "m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" }, { d: "m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" },
    { d: "M7 21h10" }, { d: "M12 3v18" }, { d: "M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" },
  ],
  alert: [{ d: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" }, { d: "M12 9v4" }, { d: "M12 17h.01" }],
  ban: [{ c: [12, 12, 10] }, { d: "m4.9 4.9 14.2 14.2" }],
  trendingDown: [{ d: "M22 17 13.5 8.5l-5 5L2 7" }, { d: "M16 17h6v-6" }],
  sparkles: [
    { d: "M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5A2 2 0 0 0 15.5 9.94l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z" },
  ],
  sliders: [{ d: "M4 21v-7" }, { d: "M4 10V3" }, { d: "M12 21v-9" }, { d: "M12 8V3" }, { d: "M20 21v-5" }, { d: "M20 12V3" }, { d: "M2 14h4" }, { d: "M10 8h4" }, { d: "M18 16h4" }],
} satisfies Record<string, Shape[]>;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 20, color, strokeWidth = 2 }: { name: IconName; size?: number; color: string; strokeWidth?: number }) {
  const shapes: Shape[] = ICONS[name];
  const common = { stroke: color, strokeWidth, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {shapes.map((s, i) =>
        "d" in s ? <Path key={i} d={s.d} {...common} />
        : "c" in s ? <Circle key={i} cx={s.c[0]} cy={s.c[1]} r={s.c[2]} {...common} />
        : <Ellipse key={i} cx={s.e[0]} cy={s.e[1]} rx={s.e[2]} ry={s.e[3]} {...common} />,
      )}
    </Svg>
  );
}

export default Icon;
