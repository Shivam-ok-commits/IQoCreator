import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      fontSize: {
        "display-1": ["96px", { lineHeight: "0.95", letterSpacing: "-0.03em", fontWeight: "800" }],
        "display-2": ["72px", { lineHeight: "1", letterSpacing: "-0.02em", fontWeight: "800" }],
        "display-3": ["64px", { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "700" }],
        "heading-1": ["48px", { lineHeight: "1.1", letterSpacing: "-0.015em", fontWeight: "700" }],
        "heading-2": ["40px", { lineHeight: "1.15", letterSpacing: "-0.01em", fontWeight: "700" }],
        "heading-3": ["32px", { lineHeight: "1.2", letterSpacing: "-0.005em", fontWeight: "600" }],
        "heading-4": ["24px", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["16px", { lineHeight: "1.6" }],
        caption: ["14px", { lineHeight: "1.5" }],
        small: ["12px", { lineHeight: "1.5" }],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        crimson: {
          50: "#FFF5F5",
          100: "#FFE0E0",
          200: "#FFC0C0",
          300: "#FF9090",
          400: "#FF5050",
          500: "#EF233C",
          600: "#D90429",
          700: "#B00020",
          800: "#8B0018",
          900: "#6B0012",
          950: "#3A0009",
        },
        surface: {
          DEFAULT: "hsl(var(--surface))",
          elevated: "hsl(var(--surface-elevated))",
          glass: "hsl(var(--surface-glass))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "24px",
        "2xl": "32px",
      },
      boxShadow: {
        glow: "0 0 30px -10px rgba(217, 4, 41, 0.3)",
        "glow-lg": "0 0 60px -15px rgba(217, 4, 41, 0.25)",
        card: "0 8px 32px -8px rgba(0,0,0,0.4)",
        "card-hover": "0 12px 48px -12px rgba(0,0,0,0.5)",
        panel: "0 4px 24px -6px rgba(0,0,0,0.3)",
      },
      backdropBlur: {
        glass: "12px",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.97)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px -8px hsl(var(--primary) / 0.3)" },
          "50%": { boxShadow: "0 0 40px -8px hsl(var(--primary) / 0.5)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.3s ease-out",
        "fade-up": "fade-up 0.4s ease-out",
        "scale-in": "scale-in 0.25s ease-out",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
