/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'media', // Use system preference
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        phase: {
          trigger: '#3b82f6',
          peak: '#ef4444',
          trough: '#f59e0b',
          slope: '#10b981',
          plateau: '#6366f1',
        },
      },
    },
  },
  plugins: [],
}
