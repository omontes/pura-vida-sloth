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
        sans: ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['Menlo', 'Monaco', 'Consolas', 'Courier New', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.5' }],      // 12px
        sm: ['0.875rem', { lineHeight: '1.5' }],     // 14px
        base: ['1rem', { lineHeight: '1.6' }],       // 16px (increased from 14px)
        lg: ['1.125rem', { lineHeight: '1.6' }],     // 18px
        xl: ['1.25rem', { lineHeight: '1.5' }],      // 20px
        '2xl': ['1.5rem', { lineHeight: '1.4' }],    // 24px (H3)
        '3xl': ['1.75rem', { lineHeight: '1.3' }],   // 28px (H2)
        '4xl': ['2rem', { lineHeight: '1.2' }],      // 32px (metadata)
        '5xl': ['2.25rem', { lineHeight: '1.2' }],   // 36px (H1)
      },
      colors: {
        // Accent Colors (light/dark mode adaptive)
        accent: {
          DEFAULT: '#0f766e',  // Teal (light mode primary)
          hover: '#0d9488',
          light: '#ccfbf1',
          dark: '#fbbf24',     // Gold (dark mode primary)
          'dark-hover': '#f59e0b',
        },
        // Semantic Colors
        success: {
          DEFAULT: '#059669',
          light: '#d1fae5',
          dark: '#10b981',
        },
        warning: {
          DEFAULT: '#d97706',
          light: '#fef3c7',
          dark: '#f59e0b',
        },
        error: {
          DEFAULT: '#dc2626',
          light: '#fee2e2',
          dark: '#f87171',
        },
        info: {
          DEFAULT: '#2563eb',
          light: '#dbeafe',
          dark: '#60a5fa',
        },
        // Chart Phase Colors (harmonized)
        phase: {
          trigger: '#2563eb',   // Blue - beginning
          peak: '#dc2626',      // Red - danger/peak
          trough: '#f59e0b',    // Amber - caution
          slope: '#059669',     // Green - growth
          plateau: '#7c3aed',   // Purple - maturity
        },
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
        DEFAULT: '0 2px 8px rgba(0, 0, 0, 0.08)',
        md: '0 2px 8px rgba(0, 0, 0, 0.08)',
        lg: '0 4px 16px rgba(0, 0, 0, 0.1)',
        xl: '0 10px 40px rgba(0, 0, 0, 0.15)',
        '2xl': '0 20px 60px rgba(0, 0, 0, 0.2)',
        'dark-sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'dark-md': '0 2px 8px rgba(0, 0, 0, 0.4)',
        'dark-lg': '0 4px 16px rgba(0, 0, 0, 0.5)',
        'dark-xl': '0 10px 40px rgba(0, 0, 0, 0.6)',
      },
      borderRadius: {
        sm: '0.375rem',   // 6px
        DEFAULT: '0.5rem', // 8px
        md: '0.5rem',     // 8px
        lg: '0.75rem',    // 12px
        xl: '1rem',       // 16px
        '2xl': '1.5rem',  // 24px
      },
      letterSpacing: {
        tight: '-0.02em',
        normal: '0',
        wide: '0.02em',
      },
    },
  },
  plugins: [],
}
