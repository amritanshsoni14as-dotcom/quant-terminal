import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "rgb(var(--term-bg) / <alpha-value>)",
          panel: "rgb(var(--term-panel) / <alpha-value>)",
          card: "rgb(var(--term-card) / <alpha-value>)",
          border: "rgb(var(--term-border) / <alpha-value>)",
          muted: "rgb(var(--term-muted) / <alpha-value>)",
          text: "rgb(var(--term-text) / <alpha-value>)",
          accent: "rgb(var(--term-accent) / <alpha-value>)",
          rain: "rgb(var(--term-rain) / <alpha-value>)",
          pos: "rgb(var(--term-pos) / <alpha-value>)",
          neg: "rgb(var(--term-neg) / <alpha-value>)",
          warn: "rgb(var(--term-warn) / <alpha-value>)",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
