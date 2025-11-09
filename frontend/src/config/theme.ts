/**
 * Theme Configuration
 *
 * Professional light/dark theme system for Pura Vida Sloth
 * Light mode is default for executive presentations
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
    };
    // Text colors
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
    };
    // Border colors
    border: {
      default: string;
      hover: string;
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
      primary: '#ffffff',
      secondary: '#f8f9fa',
      tertiary: '#f1f3f5',
    },
    text: {
      primary: '#000000',        // Pure black for maximum contrast
      secondary: '#374151',      // Darker gray for better readability
      tertiary: '#6b7280',
    },
    border: {
      default: '#d1d5db',       // Slightly darker for visibility
      hover: '#9ca3af',
    },
    chart: {
      curve: '#1E40AF',         // Professional dark blue
      curveShadow: 'rgba(30, 64, 175, 0.15)',
      separator: '#94a3b8',     // More visible separators
      axisText: '#000000',      // Pure black for axes
      nodeStroke: '#ffffff',
      labelBackground: 'rgba(255, 255, 255, 0.98)',  // More opaque
      labelBorder: 'rgba(0, 0, 0, 0.15)',           // More visible border
    },
    interactive: {
      primary: '#2563eb',
      primaryHover: '#1d4ed8',
      secondary: '#60a5fa',
      secondaryHover: '#3b82f6',
    },
  },
};

export const darkTheme: Theme = {
  mode: 'dark',
  colors: {
    background: {
      primary: '#0c111b',
      secondary: '#1a1d23',
      tertiary: '#2a2d35',
    },
    text: {
      primary: '#f9fafb',
      secondary: '#d1d5db',
      tertiary: '#9ca3af',
    },
    border: {
      default: '#374151',
      hover: '#4b5563',
    },
    chart: {
      curve: '#60a5fa',
      curveShadow: 'rgba(96, 165, 250, 0.2)',
      separator: '#4b5563',
      axisText: '#f9fafb',
      nodeStroke: '#1a1d23',
      labelBackground: 'rgba(26, 29, 35, 0.95)',
      labelBorder: 'rgba(255, 255, 255, 0.1)',
    },
    interactive: {
      primary: '#3b82f6',
      primaryHover: '#2563eb',
      secondary: '#60a5fa',
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
