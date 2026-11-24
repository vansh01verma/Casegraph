export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 950: '#050d1a', 900: '#08142a', 800: '#0b1a2e', 700: '#12263f', 600: '#1b3553' },
        char: { 900: '#0f1318', 800: '#161b22', 700: '#20262e', 600: '#2b323c' },
        cyan: { 350: '#4fd8f2' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
    },
  },
  plugins: [],
}
