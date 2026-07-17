export interface ThemeTokens {
  background: string;
  surface: string;
  surfaceElevated: string;
  primary: string;
  secondary: string;
  accent: string;
  border: string;
  textPrimary: string;
  textSecondary: string;
  success: string;
  warning: string;
  danger: string;
  glow: string;
  gradient: string;
  radialGlow: string;
}

export const FALLBACK_THEME: ThemeTokens = {
  background: "#090a0f",
  surface: "#111318",
  surfaceElevated: "#1a1c23",
  primary: "#4f6ef7",
  secondary: "#7c5cfc",
  accent: "#6d28d9",
  border: "rgba(255,255,255,0.06)",
  textPrimary: "#f1f5f9",
  textSecondary: "#94a3b8",
  success: "#22c55e",
  warning: "#f59e0b",
  danger: "#ef4444",
  glow: "rgba(79,110,247,0.15)",
  gradient: "linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #090a0f 100%)",
  radialGlow: "radial-gradient(ellipse at 30% 20%, rgba(79,110,247,0.08) 0%, transparent 60%)",
};
