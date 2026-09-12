/** @type {import('tailwindcss').Config} */
// Design tokens (brief §8). Warm neutrals, one accent (teal), three semantic
// colours that mean the same thing everywhere. Red is danger only — never a
// decline, never no_action.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    fontFamily: {
      sans: [
        "system-ui", "-apple-system", "Segoe UI", "Roboto",
        "Noto Sans", "Noto Sans Devanagari", "sans-serif",
      ],
    },
    fontSize: {
      // rem so the user's system font scale (often 120–130% on cheap phones) applies.
      sm: ["0.875rem", { lineHeight: "1.5" }],
      base: ["1rem", { lineHeight: "1.5" }],
      lg: ["1.25rem", { lineHeight: "1.4" }],
      xl: ["1.5rem", { lineHeight: "1.3" }],
      "2xl": ["2rem", { lineHeight: "1.2" }],
      "3xl": ["2.5rem", { lineHeight: "1.1" }],
    },
    extend: {
      colors: {
        paper: "#faf8f4",      // page background
        card: "#ffffff",
        sand: "#f1ede4",       // soft neutral surfaces (no_action, chips)
        ink: { DEFAULT: "#1f1d1a", soft: "#5a5650", mute: "#6b665e" },
        line: "#e4dfd5",
        accent: { DEFAULT: "#0f766e", strong: "#0b5d57", soft: "#e0f2f0" },
        safe:   { DEFAULT: "#1a7f37", soft: "#e6f4ea", ink: "#14602a" },
        care:   { DEFAULT: "#b45309", soft: "#fdf1e3", ink: "#8a3f06" },
        danger: { DEFAULT: "#b91c1c", soft: "#fdecec", ink: "#8f1414" },
      },
      spacing: { 18: "72px" },
      borderRadius: { xl: "16px", "2xl": "20px" },
      boxShadow: { card: "0 1px 2px rgba(31,29,26,0.05), 0 2px 8px rgba(31,29,26,0.04)" },
      minHeight: { touch: "48px", cta: "56px" },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.55" } },
      },
      animation: {
        rise: "rise 200ms ease-out both",
        pulseSoft: "pulseSoft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
