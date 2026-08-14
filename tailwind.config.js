/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        page: 'var(--color-page)',
        card: 'var(--color-card)',
        elevated: 'var(--color-elevated)',
        ink: 'var(--color-ink)',
        muted: 'var(--color-muted)',
        subtle: 'var(--color-subtle)',
        line: 'var(--color-line)',
        divider: 'var(--color-divider)',
        accent: 'var(--color-accent)',
        'accent-soft': 'var(--color-accent-soft)',
        'on-accent': 'var(--color-on-accent)',
        teal: 'var(--color-teal)',
        'teal-soft': 'var(--color-teal-soft)',
        nav: 'var(--color-nav)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
