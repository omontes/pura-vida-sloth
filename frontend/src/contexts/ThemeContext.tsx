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
  // ALWAYS default to light mode (ignore localStorage for now)
  const [themeMode, setThemeModeState] = useState<ThemeMode>('light');

  const [theme, setTheme] = useState<Theme>(() => getTheme('light'));

  useEffect(() => {
    // Update theme object when mode changes
    setTheme(getTheme(themeMode));

    // Save preference
    localStorage.setItem('theme-mode', themeMode);

    // Update document class for Tailwind dark mode
    if (themeMode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [themeMode]);

  const toggleTheme = () => {
    setThemeModeState(prev => prev === 'light' ? 'dark' : 'light');
  };

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode);
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
