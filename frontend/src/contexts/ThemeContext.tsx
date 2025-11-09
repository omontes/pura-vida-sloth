/**
 * Theme Context
 *
 * React context for managing theme state across the application
 * Light mode is default
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ThemeMode, Theme, getTheme } from '@/config/theme';

interface ThemeContextType {
  theme: Theme;
  themeMode: ThemeMode;
  toggleTheme: () => void;
  setThemeMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  // Auto-detect system preference and listen for changes
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    // Detect system preference on startup
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  const [theme, setTheme] = useState<Theme>(() => getTheme(themeMode));

  useEffect(() => {
    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      setThemeModeState(e.matches ? 'dark' : 'light');
    };

    // Modern browsers
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, []);

  useEffect(() => {
    // Update theme object when mode changes
    setTheme(getTheme(themeMode));

    // Update document class for Tailwind dark mode
    if (themeMode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [themeMode]);

  const toggleTheme = () => {
    // No-op: theme follows system preference automatically
  };

  const setThemeMode = (mode: ThemeMode) => {
    // No-op: theme follows system preference automatically
  };

  return (
    <ThemeContext.Provider value={{ theme, themeMode, toggleTheme, setThemeMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
