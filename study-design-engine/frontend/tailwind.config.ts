import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        darpan: {
          bg: "#0A0A0A",
          surface: "#111111",
          elevated: "#1A1A1A",
          border: "#2A2A2A",
          "border-active": "#333333",
          lime: "#C8FF00",
          "lime-dim": "#9ACC00",
          cyan: "#00D4FF",
          "cyan-dim": "#00A8CC",
          success: "#00FF88",
          warning: "#FFB800",
          error: "#FF4444",
        },
      },
      fontFamily: {
        sans: ["var(--font-space-grotesk)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      boxShadow: {
        "glow-lime": "0 0 20px rgba(200, 255, 0, 0.3)",
        "glow-cyan": "0 0 20px rgba(0, 212, 255, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
