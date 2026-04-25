import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: "#0f172a",
        panel: "#111827",
        accent: "#f59e0b",
        mist: "#d1d5db",
        success: "#10b981",
        danger: "#ef4444"
      },
      fontFamily: {
        display: ["'IBM Plex Sans'", "sans-serif"],
        body: ["'IBM Plex Sans'", "sans-serif"]
      },
      boxShadow: {
        frame: "0 20px 45px rgba(15, 23, 42, 0.35)"
      }
    }
  },
  plugins: []
} satisfies Config;

