import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Dark theme - Midnight/Zinc backgrounds
        background: {
          DEFAULT: "#09090b", // zinc-950
          secondary: "#18181b", // zinc-900
          tertiary: "#27272a", // zinc-800
          card: "rgba(24, 24, 27, 0.6)", // translucent zinc-900
        },
        // Modern gradients and accents
        accent: {
          DEFAULT: "#0ea5e9", // sky-500
          hover: "#0284c7", // sky-600
          light: "#38bdf8", // sky-400
          dark: "#0369a1", // sky-700
          purple: "#8b5cf6", // violet-500
        },
        // Text colors
        foreground: {
          DEFAULT: "#f8fafc", // slate-50
          muted: "#a1a1aa", // zinc-400
          subtle: "#71717a", // zinc-500
        },
        // Border colors
        border: {
          DEFAULT: "#27272a", // zinc-800
          hover: "#3f3f46", // zinc-700
          glow: "rgba(14, 165, 233, 0.3)", // sky glow for vibrant borders
        },
        // Semantic colors
        success: "#22c55e",
        warning: "#f59e0b",
        error: "#ef4444",
        info: "#3b82f6",
      },
      fontFamily: {
        sans: ["var(--font-outfit)", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-in": "slideIn 0.3s ease-out",
        "float": "float 6s ease-in-out infinite",
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
