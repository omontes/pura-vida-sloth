/**
 * Header Component
 *
 * Professional header with theme toggle and export functionality
 */

import { useTheme } from '@/contexts/ThemeContext';

interface HeaderProps {
  industry?: string;
  onExport?: () => void;
}

export default function Header({ industry, onExport }: HeaderProps) {
  const { themeMode, toggleTheme } = useTheme();

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Pura Vida Sloth
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Strategic Technology Market Research
            </p>
          </div>
          <div className="flex items-center gap-4">
            {industry && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Industry:{' '}
                <span className="font-semibold text-gray-900 dark:text-white">
                  {industry}
                </span>
              </div>
            )}

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Toggle theme"
              title={`Switch to ${themeMode === 'light' ? 'dark' : 'light'} mode`}
            >
              {themeMode === 'light' ? (
                // Moon icon for dark mode
                <svg
                  className="w-5 h-5 text-gray-700"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
              ) : (
                // Sun icon for light mode
                <svg
                  className="w-5 h-5 text-gray-300"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
              )}
            </button>

            {/* Export Button */}
            {onExport && (
              <button
                onClick={onExport}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Export Report
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
