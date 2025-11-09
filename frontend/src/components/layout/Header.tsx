/**
 * Header Component
 *
 * Professional header for the application
 */

interface HeaderProps {
  industry?: string;
  onExport?: () => void;
}

export default function Header({ industry, onExport }: HeaderProps) {
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
