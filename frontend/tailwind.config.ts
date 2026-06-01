import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
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
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Quorum agent role colors — locked per docs/ia.md
        "agent-hypothesis": "hsl(217, 91%, 60%)",
        "agent-test-chooser": "hsl(160, 84%, 39%)",
        "agent-challenger": "hsl(0, 84%, 60%)",
        "agent-stewardship": "hsl(43, 96%, 56%)",
        "agent-checklist": "hsl(280, 91%, 60%)",
        // clinical-trust helper tokens
        "surface-2": "var(--surface-2)",
        "ink-2": "var(--ink-2)",
        faint: "var(--faint)",
        "line-strong": "var(--line-strong)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        line: "hsl(var(--border))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        "card-1": "0 1px 2px rgba(15,23,42,.05)",
        "card-2": "0 1px 2px rgba(15,23,42,.04), 0 10px 30px rgba(15,23,42,.07)",
      },
      keyframes: {
        blink: { "0%,60%,100%": { opacity: "0.25" }, "30%": { opacity: "1" } },
        livepulse: {
          "0%": { boxShadow: "0 0 0 0 rgba(22,163,74,.45)" },
          "70%": { boxShadow: "0 0 0 7px rgba(22,163,74,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(22,163,74,0)" },
        },
      },
      animation: { blink: "blink 1.2s infinite", livepulse: "livepulse 1.6s infinite" },
    },
  },
  plugins: [animate],
};

export default config;
