import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
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
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        "glow-lime": "0 0 20px rgba(200, 255, 0, 0.3)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};

export default config;
