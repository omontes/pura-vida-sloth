/**
 * Design Tokens for Canopy Intelligence
 * Centralized design system constants for typography, colors, spacing, shadows, and radii
 */

// Typography Scale (16px base, 1.25 ratio)
export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, Avenir, Helvetica, Arial, sans-serif',
    mono: 'Menlo, Monaco, Consolas, "Courier New", monospace',
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px (body text - increased from 14px)
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px (H3)
    '3xl': '1.75rem', // 28px (H2)
    '4xl': '2rem',    // 32px (metadata numbers)
    '5xl': '2.25rem', // 36px (H1)
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,   // Headings
    normal: 1.5,  // Body
    relaxed: 1.6, // Reading content
  },
  letterSpacing: {
    tight: '-0.02em',  // Large headings
    normal: '0',       // Body
    wide: '0.02em',    // Small caps
  },
} as const;

// Color Palette - Professional, Nutrient-inspired
export const colors = {
  // Light Mode
  light: {
    background: {
      primary: '#ffffff',     // Pure white
      secondary: '#f8f9fa',   // Subtle gray
      tertiary: '#f1f3f5',    // Light gray
      card: '#ffffff',        // White cards with shadows
    },
    text: {
      primary: '#0a0a0a',     // Near black (softer than pure black)
      secondary: '#525252',   // Medium gray
      tertiary: '#737373',    // Light gray
      inverse: '#ffffff',     // For dark backgrounds
    },
    border: {
      subtle: '#e5e5e5',      // Very light gray
      default: '#d4d4d4',     // Light gray
      strong: '#a3a3a3',      // Medium gray
    },
    accent: {
      primary: '#0f766e',     // Teal - trust, intelligence
      hover: '#0d9488',       // Teal hover
      light: '#ccfbf1',       // Teal background
    },
    semantic: {
      success: '#059669',     // Green
      successLight: '#d1fae5',
      warning: '#d97706',     // Amber
      warningLight: '#fef3c7',
      error: '#dc2626',       // Red
      errorLight: '#fee2e2',
      info: '#2563eb',        // Blue
      infoLight: '#dbeafe',
    },
  },

  // Dark Mode - Sophisticated
  dark: {
    background: {
      primary: '#0a0a0a',     // Deep black
      secondary: '#171717',   // Charcoal
      tertiary: '#1f1f1f',    // Dark gray
      card: '#1a1a1a',        // Dark cards with borders
    },
    text: {
      primary: '#fafafa',     // Near white
      secondary: '#d4d4d4',   // Light gray
      tertiary: '#a3a3a3',    // Medium gray
      inverse: '#0a0a0a',     // For light backgrounds
    },
    border: {
      subtle: '#262626',      // Very dark gray
      default: '#404040',     // Dark gray
      strong: '#525252',      // Medium gray
    },
    accent: {
      primary: '#fbbf24',     // Gold - premium, insight (Nutrient-inspired)
      hover: '#f59e0b',       // Gold hover
      light: '#451a03',       // Gold background (dark)
    },
    semantic: {
      success: '#10b981',     // Bright green
      successLight: '#064e3b',
      warning: '#f59e0b',     // Bright amber
      warningLight: '#451a03',
      error: '#f87171',       // Bright red
      errorLight: '#450a0a',
      info: '#60a5fa',        // Bright blue
      infoLight: '#1e3a8a',
    },
  },

  // Chart Colors - Harmonized with semantic palette
  chart: {
    phases: {
      innovationTrigger: '#2563eb',  // Blue - beginning
      peak: '#dc2626',               // Red - danger/peak
      trough: '#f59e0b',             // Amber - caution
      slope: '#059669',              // Green - growth
      plateau: '#7c3aed',            // Purple - maturity
    },
  },
} as const;

// Spacing Scale (4px base)
export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
} as const;

// Shadow System - Elevation
export const shadows = {
  light: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 2px 8px rgba(0, 0, 0, 0.08)',
    lg: '0 4px 16px rgba(0, 0, 0, 0.1)',
    xl: '0 10px 40px rgba(0, 0, 0, 0.15)',
    '2xl': '0 20px 60px rgba(0, 0, 0, 0.2)',
  },
  dark: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
    md: '0 2px 8px rgba(0, 0, 0, 0.4)',
    lg: '0 4px 16px rgba(0, 0, 0, 0.5)',
    xl: '0 10px 40px rgba(0, 0, 0, 0.6)',
    '2xl': '0 20px 60px rgba(0, 0, 0, 0.7)',
  },
} as const;

// Border Radii
export const radii = {
  none: '0',
  sm: '0.375rem',   // 6px
  md: '0.5rem',     // 8px
  lg: '0.75rem',    // 12px
  xl: '1rem',       // 16px
  '2xl': '1.5rem',  // 24px
  full: '9999px',   // Circular
} as const;

// Transitions
export const transitions = {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  normal: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '500ms cubic-bezier(0.4, 0, 0.2, 1)',
} as const;

// Z-Index Scale
export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1100,
  fixed: 1200,
  modal: 1300,
  popover: 1400,
  tooltip: 1500,
} as const;

// Breakpoints (sync with Tailwind)
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Export all tokens as default
export default {
  typography,
  colors,
  spacing,
  shadows,
  radii,
  transitions,
  zIndex,
  breakpoints,
};
