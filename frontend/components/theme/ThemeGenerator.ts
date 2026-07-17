import { ThemeTokens, FALLBACK_THEME } from "./ThemeTokens";

interface HSL {
  h: number;
  s: number;
  l: number;
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function rgbToHsl(r: number, g: number, b: number): HSL {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l: l * 100 };
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;
  return { h: h * 360, s: s * 100, l: l * 100 };
}

function hslToHex(h: number, s: number, l: number): string {
  const s2 = s / 100, l2 = l / 100;
  const a = s2 * Math.min(l2, 1 - l2);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l2 - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

function parseHex(hex: string): number {
  return parseInt(hex.replace("#", ""), 16);
}

function blendWithBase(hex: string, base: string, opacity: number): string {
  const [r1, g1, b1] = hexToRgb(hex);
  const [r2, g2, b2] = hexToRgb(base);
  const r = Math.round(r1 * opacity + r2 * (1 - opacity));
  const g = Math.round(g1 * opacity + g2 * (1 - opacity));
  const b = Math.round(b1 * opacity + b2 * (1 - opacity));
  return `rgb(${r},${g},${b})`;
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export function generateTheme(colors: string[]): ThemeTokens {
  if (!colors || colors.length === 0) return { ...FALLBACK_THEME };

  const sorted = [...colors].sort(
    (a, b) => {
      const lumA = hexToRgb(a)[0] * 0.2126 + hexToRgb(a)[1] * 0.7152 + hexToRgb(a)[2] * 0.0722;
      const lumB = hexToRgb(b)[0] * 0.2126 + hexToRgb(b)[1] * 0.7152 + hexToRgb(b)[2] * 0.0722;
      return lumB - lumA;
    },
  );

  const lightest = sorted[sorted.length - 1] || colors[0];
  const darkest = sorted[0] || colors[colors.length - 1];
  const midtones = colors.slice(1, -1);
  const primaryColor = midtones.length > 0 ? pick(midtones) : colors[1] || colors[0];
  const accentColor = colors.length > 1 ? colors[1] : primaryColor;

  const hsl = rgbToHsl(...hexToRgb(primaryColor));
  const accentHsl = rgbToHsl(...hexToRgb(accentColor));

  const primary = hslToHex(hsl.h, Math.min(hsl.s + 15, 85), Math.min(hsl.l + 20, 70));
  const secondary = hslToHex(
    (hsl.h + 40) % 360,
    Math.min(hsl.s + 10, 70),
    Math.min(hsl.l + 15, 65),
  );
  const accent = hslToHex(
    accentHsl.h,
    Math.min(accentHsl.s + 20, 80),
    Math.min(accentHsl.l + 25, 75),
  );

  const bgDark = hslToHex(hsl.h, Math.min(hsl.s * 0.3, 20), 5);
  const bgMid = hslToHex(hsl.h, Math.min(hsl.s * 0.2, 15), 8);
  const bgElevated = hslToHex(hsl.h, Math.min(hsl.s * 0.15, 12), 12);

  return {
    background: bgDark,
    surface: blendWithBase(bgMid, "#0a0a0a", 0.7),
    surfaceElevated: blendWithBase(bgElevated, "#141414", 0.5),
    primary,
    secondary,
    accent,
    border: `rgba(${hexToRgb(primary).join(",")},0.08)`,
    textPrimary: "#f1f5f9",
    textSecondary: "#94a3b8",
    success: "#22c55e",
    warning: "#f59e0b",
    danger: "#ef4444",
    glow: `rgba(${hexToRgb(primary).join(",")},0.12)`,
    gradient: `linear-gradient(135deg, ${bgDark} 0%, ${blendWithBase(bgMid, "#0f0f0f", 0.5)} 50%, ${bgDark} 100%)`,
    radialGlow: `radial-gradient(ellipse at 30% 20%, rgba(${hexToRgb(primary).join(",")},0.08) 0%, transparent 60%)`,
  };
}

export function generateFallbackTheme(): ThemeTokens {
  return { ...FALLBACK_THEME };
}
