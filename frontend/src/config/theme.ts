/**
 * Theme Configuration
 *
 * Professional light/dark theme system for Canopy Intelligence
 * Light mode is default for executive presentations
 * Inspired by modern SaaS design with teal (light) and gold (dark) accents
 */

export type ThemeMode = 'light' | 'dark';

export interface Theme {
  mode: ThemeMode;
  colors: {
    // Background colors
    background: {
      primary: string;
      secondary: string;
      tertiary: string;
      card: string;
    };
    // Text colors
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
    };
    // Border colors
    border: {
      subtle: string;
      default: string;
      strong: string;
    };
    // Accent colors (brand identity)
    accent: {
      primary: string;
      hover: string;
      light: string;
    };
    // Chart colors
    chart: {
      curve: string;
      curveShadow: string;
      separator: string;
      axisText: string;
      nodeStroke: string;
      labelBackground: string;
      labelBorder: string;
    };
    // Interactive elements
    interactive: {
      primary: string;
      primaryHover: string;
      secondary: string;
      secondaryHover: string;
    };
  };
}

export const lightTheme: Theme = {
  mode: 'light',
  colors: {
    background: {
      primary: '#ffffff',       // Pure white
      secondary: '#f8f9fa',     // Subtle gray
      tertiary: '#f1f3f5',      // Light gray
      card: '#ffffff',          // White cards with shadows
    },
    text: {
      primary: '#0a0a0a',       // Near black (softer than pure black)
      secondary: '#525252',     // Medium gray
      tertiary: '#737373',      // Light gray
    },
    border: {
      subtle: '#e5e5e5',        // Very light gray
      default: '#d4d4d4',       // Light gray
      strong: '#a3a3a3',        // Medium gray
    },
    accent: {
      primary: '#0f766e',       // Teal - trust, intelligence
      hover: '#0d9488',         // Teal hover
      light: '#ccfbf1',         // Teal background
    },
    chart: {
      curve: '#0f766e',         // Teal accent (matches brand identity)
      curveShadow: 'rgba(15, 118, 110, 0.15)',
      separator: '#94a3b8',     // More visible separators
      axisText: '#111827',      // Matches header text-gray-900 for consistency
      nodeStroke: '#ffffff',
      labelBackground: 'rgba(255, 255, 255, 0.98)',  // More opaque
      labelBorder: 'rgba(0, 0, 0, 0.15)',           // More visible border
    },
    interactive: {
      primary: '#0f766e',       // Teal (matches accent)
      primaryHover: '#0d9488',  // Teal hover
      secondary: '#60a5fa',     // Blue
      secondaryHover: '#3b82f6',
    },
  },
};

export const darkTheme: Theme = {
  mode: 'dark',
  colors: {
    background: {
      primary: '#0a0a0a',       // Deep black
      secondary: '#171717',     // Charcoal
      tertiary: '#1f1f1f',      // Dark gray
      card: '#1a1a1a',          // Dark cards with borders
    },
    text: {
      primary: '#fafafa',       // Near white
      secondary: '#d4d4d4',     // Light gray
      tertiary: '#a3a3a3',      // Medium gray
    },
    border: {
      subtle: '#262626',        // Very dark gray
      default: '#404040',       // Dark gray
      strong: '#525252',        // Medium gray
    },
    accent: {
      primary: '#fbbf24',       // Gold - premium, insight (Nutrient-inspired)
      hover: '#f59e0b',         // Gold hover
      light: '#451a03',         // Gold background (dark)
    },
    chart: {
      curve: '#60a5fa',         // Lighter blue for dark mode
      curveShadow: 'rgba(96, 165, 250, 0.2)',
      separator: '#9ca3af',     // Lighter gray for visibility in dark mode
      axisText: '#ffffff',      // Matches header text-white for consistency
      nodeStroke: '#1a1a1a',
      labelBackground: 'rgba(26, 26, 26, 0.95)',
      labelBorder: 'rgba(255, 255, 255, 0.1)',
    },
    interactive: {
      primary: '#fbbf24',       // Gold (matches accent)
      primaryHover: '#f59e0b',  // Gold hover
      secondary: '#60a5fa',     // Blue
      secondaryHover: '#93c5fd',
    },
  },
};

/**
 * Get theme object based on mode
 */
export function getTheme(mode: ThemeMode): Theme {
  return mode === 'dark' ? darkTheme : lightTheme;
}
