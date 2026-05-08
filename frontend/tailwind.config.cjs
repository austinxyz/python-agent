/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
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
        // Notion design tokens — see docs/design/notion.md
        notion: {
          // Brand
          primary: "#5645d4",
          "primary-pressed": "#4534b3",
          "primary-deep": "#3a2a99",
          "brand-navy": "#0a1530",
          "brand-navy-deep": "#070f24",
          "brand-purple-300": "#d6b6f6",
          "brand-purple-800": "#391c57",
          "brand-orange": "#dd5b00",
          "brand-orange-deep": "#793400",
          "brand-green": "#1aae39",
          // Card tints (for differentiating templates / tags)
          "tint-peach": "#ffe8d4",
          "tint-rose": "#fde0ec",
          "tint-mint": "#d9f3e1",
          "tint-lavender": "#e6e0f5",
          "tint-sky": "#dcecfa",
          "tint-yellow": "#fef7d6",
          "tint-cream": "#f8f5e8",
          "tint-gray": "#f0eeec",
          // Surfaces
          canvas: "#ffffff",
          surface: "#f6f5f4",
          "surface-soft": "#fafaf9",
          // Hairlines
          hairline: "#e5e3df",
          "hairline-soft": "#ede9e4",
          "hairline-strong": "#c8c4be",
          // Ink
          "ink-deep": "#000000",
          ink: "#1a1a1a",
          charcoal: "#37352f",
          slate: "#5d5b54",
          steel: "#787671",
          stone: "#a4a097",
          "muted-text": "#bbb8b1",
          "on-dark": "#ffffff",
          "on-dark-muted": "#a4a097",
          // Semantic
          success: "#1aae39",
          warning: "#dd5b00",
          error: "#e03131",
          "link-blue": "#0075de",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
