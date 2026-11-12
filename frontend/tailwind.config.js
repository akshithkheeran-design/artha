/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void: '#040811',
        abyss: '#070e1c',
        panel: '#0b1628',
        edge: '#16263f',
        cyan: { 300: '#7ff3ff', 400: '#22e3f5', 500: '#06c3d9' },
        neon: { magenta: '#ff3df2', green: '#2bff9e', amber: '#ffc93d', red: '#ff4d6d', violet: '#9b7bff' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['Orbitron', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(34,227,245,.25), 0 0 24px -4px rgba(34,227,245,.35)',
        glowm: '0 0 0 1px rgba(255,61,242,.3), 0 0 24px -4px rgba(255,61,242,.4)',
      },
      keyframes: {
        scan: { '0%': { transform: 'translateY(-100%)' }, '100%': { transform: 'translateY(100vh)' } },
        pulseDot: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.25 } },
        rise: { '0%': { opacity: 0, transform: 'translateY(8px)' }, '100%': { opacity: 1, transform: 'none' } },
        spinSlow: { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        scan: 'scan 6s linear infinite',
        pulseDot: 'pulseDot 1.6s ease-in-out infinite',
        rise: 'rise .45s ease-out both',
        spinSlow: 'spinSlow 14s linear infinite',
      },
    },
  },
  plugins: [],
}
