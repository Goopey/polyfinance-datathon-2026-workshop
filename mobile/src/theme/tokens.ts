/**
 * Couleurs, espacements, rayons. Contraste élevé ; la couleur n'est jamais le seul porteur d'information
 * (chaque état a aussi une icône et un libellé). Conception : docs/07_UX_UI.md
 */
export const colors = {
  bg: "#F6F7F9",
  surface: "#FFFFFF",
  surfaceMuted: "#EEF1F5",
  border: "#D5DBE3",
  text: "#14181F",
  textMuted: "#4A5565",
  primary: "#1F4FD1",
  primaryText: "#FFFFFF",
  // Adéquation et statuts
  good: "#13703F",
  goodBg: "#E3F4EA",
  warn: "#8A5A00",
  warnBg: "#FCF1D9",
  bad: "#A12626",
  badBg: "#FBE5E5",
  neutral: "#4A5565",
  neutralBg: "#EEF1F5",
  // Étiquettes fait / hypothèse / scénario
  hypothesis: "#6B3FA0",
  hypothesisBg: "#F1EAFA",
  scenario: "#0D6B74",
  scenarioBg: "#E2F4F5",
  // Bandeau de simulation
  banner: "#14181F",
  bannerText: "#FFFFFF",
  mockBanner: "#8A5A00",
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { sm: 6, md: 10, lg: 16, pill: 999 } as const;

/** Zone tactile minimale (accessibilité). */
export const touchMin = 44;
