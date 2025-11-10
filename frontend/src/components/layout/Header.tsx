/**
 * Header Component
 *
 * Professional two-tier header for Canopy Intelligence
 * Features: Logo, branding, industry context bar (mobile), export functionality
 * Pattern: Main header + sub-bar (mobile/tablet) for clean hierarchy
 */

interface HeaderProps {
  industry?: string;
  onExport?: () => void;
}

export default function Header({ industry, onExport }: HeaderProps) {
  return (
    <>
      {/* Main Header */}
      <header className="bg-white dark:bg-[#0a0a0a] border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50 backdrop-blur-sm bg-white/95 dark:bg-[#0a0a0a]/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-3 sm:py-4 md:py-5 lg:py-6">
          <div className="flex items-center justify-between gap-4 sm:gap-6 md:gap-8">
            {/* Logo and Branding */}
            <div className="flex items-center gap-2 sm:gap-4">
              {/* Logo Icon - Network Intelligence Design */}
              <img
                src="/logo-icon.svg"
                alt="Canopy Intelligence - Network Intelligence Logo"
                className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14"
              />

              {/* Brand Name and Tagline */}
              <div>
                <h1 className="text-2xl lg:text-[1.95rem] lg:leading-tight font-bold text-gray-900 dark:text-white tracking-tight">
                  Canopy Intelligence
                </h1>
                <p className="hidden sm:block text-[0.615rem] lg:text-[0.8rem] sm:leading-tight lg:leading-tight text-gray-600 dark:text-gray-400 mt-0.5">
                  Strategic Technology Market Intelligence
                </p>
              </div>
            </div>

            {/* Right Side: Industry Badge (desktop) + Export Button */}
            <div className="flex items-center gap-2 sm:gap-3 md:gap-4 lg:gap-6">
              {/* Industry Badge - Large Desktop only */}
              {industry && (
                <div className="hidden lg:flex px-4 py-2.5 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400 mr-2">Industry:</span>
                  <span className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                    {industry}
                  </span>
                </div>
              )}

              {/* Export Button - Matched height with badge (Desktop only) */}
              {onExport && (
                <button
                  onClick={onExport}
                  className="hidden lg:flex px-3 py-2.5 sm:px-6 sm:py-2.5 bg-accent hover:bg-accent-hover dark:bg-accent-dark dark:hover:bg-accent-dark-hover text-white rounded-lg transition-all duration-200 font-medium shadow-md hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] items-center gap-2 border border-transparent hover:border-accent-hover dark:hover:border-accent-dark-hover"
                  title="Print or save as PDF"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="hidden xl:inline">Export Report</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Industry Context Sub-Bar - Mobile/Tablet/iPad (below 1024px) */}
      {industry && (
        <div className="block lg:hidden bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-[60px] sm:top-[76px] z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5">
            <div className="flex items-center justify-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Industry:</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                {industry}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
