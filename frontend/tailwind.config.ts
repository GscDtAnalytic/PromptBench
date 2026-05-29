import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // paleta sóbria — densidade de informação > enfeite
        slate: {
          950: "#0a0e1a",
          900: "#0f172a",
          800: "#1e293b",
          700: "#334155",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Inter", "sans-serif"],
        mono: ["ui-monospace", "Menlo", "Monaco", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
