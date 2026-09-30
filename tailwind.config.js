/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/renderer/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        planka: {
          bg: '#1e2023',
          sidebar: '#18191c',
          column: '#282b30',
          card: '#36393f',
          cardHover: '#40444b',
          border: '#4f545c',
          text: '#dcddde',
          textMuted: '#8e9297',
          accent: '#5865f2',
          accentHover: '#4752c4',
          success: '#3ba55d',
          danger: '#ed4245',
          warning: '#faa81a'
        }
      }
    },
  },
  plugins: [],
}
