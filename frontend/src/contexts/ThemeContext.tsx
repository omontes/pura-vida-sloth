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
  // Force light mode always (professional presentation standard)
  const [themeMode, setThemeModeState] = useState<ThemeMode>('light');

  const [theme, setTheme] = useState<Theme>(() => getTheme('light'));

  useEffect(() => {
    // Ensure light mode always (remove any dark class)
    document.documentElement.classList.remove('dark');
  }, []);

  const toggleTheme = () => {
    // No-op: light mode forced (professional presentation standard)
  };

  const setThemeMode = (mode: ThemeMode) => {
    // No-op: light mode forced (professional presentation standard)
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
