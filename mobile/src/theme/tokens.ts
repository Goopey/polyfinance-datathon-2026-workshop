/**
 * Couleurs, espacements, rayons. Conception : docs/07_UX_UI.md
 *
 * Palette de base (« vert profond → menthe ») : #051F20 · #0B2B26 · #163832 · #235347 · #8EB69B · #DAF1DE.
 * Les états (adéquation, confiance, étiquettes) utilisent des tons « pierres précieuses » qui se fondent
 * dans le vert sans s'y confondre : jade, ambre doré, corail, pervenche, lavande, aqua.
 * Contraste ≥ 4,5:1 sur les surfaces ; la couleur n'est jamais le seul porteur d'information
 * (chaque état a aussi une icône ou une jauge et un libellé).
 */
export const palette = {
  g900: "#051F20",
  g800: "#0B2B26",
  g700: "#163832",
  g600: "#235347",
  g300: "#8EB69B",
  g100: "#DAF1DE",
} as const;

export const colors = {
  bg: palette.g900,
  surface: palette.g800,
  surfaceRaised: palette.g700,
  surfaceMuted: "#0F302A",
  border: "#1C463C",
  borderStrong: palette.g600,
  text: "#E9F7EC",
  textMuted: palette.g300,
  textSubtle: "#7FA58C",
  primary: palette.g300,
  primaryText: palette.g900,
  mint: palette.g100,
  link: palette.g100,
  glow: palette.g600,
  gold: "#E9C46A",
  // Adéquation et statuts
  good: "#5EE3A1",
  goodBg: "rgba(94,227,161,0.12)",
  warn: "#F2C46D",
  warnBg: "rgba(242,196,109,0.12)",
  bad: "#FF9B8F",
  badBg: "rgba(255,155,143,0.12)",
  info: "#A9C2FF",
  infoBg: "rgba(169,194,255,0.12)",
  neutral: "#B7CDBF",
  neutralBg: "rgba(218,241,222,0.08)",
  // Étiquettes fait / hypothèse / scénario
  hypothesis: "#CDB8F5",
  hypothesisBg: "rgba(205,184,245,0.12)",
  scenario: "#7FDBD0",
  scenarioBg: "rgba(127,219,208,0.12)",
  overlay: "rgba(2,12,12,0.72)",
} as const;

/** Couleur hexadécimale → rgba avec l'opacité donnée. */
export function alpha(hex: string, a: number): string {
  const h = hex.replace("#", "");
  if (h.length !== 6) return hex;
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { sm: 8, md: 12, lg: 20, xl: 28, pill: 999 } as const;

/** Zone tactile minimale (accessibilité). */
export const touchMin = 44;
