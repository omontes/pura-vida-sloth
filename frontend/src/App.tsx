import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Header from './components/layout/Header'
import HypeCycleChart from './components/charts/HypeCycleChart'
import Neo4jGraphViz from './components/graph/Neo4jGraphViz'
import Card, { CardHeader, CardTitle, CardDescription } from './components/ui/Card'
import Button from './components/ui/Button'
import type { HypeCycleChartData } from './types/hypeCycle'
import './styles/print.css'

function App() {
  const [selectedTechId, setSelectedTechId] = useState<string | null>(null)
  const [showGraph, setShowGraph] = useState(false)

  // Fetch hype cycle data JSON
  const { data, isLoading, error } = useQuery<HypeCycleChartData>({
    queryKey: ['hypeCycleData'],
    queryFn: async () => {
      const response = await fetch('/data/hype_cycle_chart.json')
      if (!response.ok) {
        throw new Error('Failed to fetch hype cycle data')
      }
      return response.json()
    },
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-accent dark:border-accent-dark mx-auto mb-6"></div>
          <p className="text-xl text-gray-600 dark:text-gray-400">Loading market intelligence data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#0a0a0a] flex items-center justify-center">
        <Card className="max-w-md text-center" elevation="elevated">
          <div className="text-error dark:text-error-dark">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h2 className="text-2xl font-bold mb-3">Error Loading Data</h2>
            <p className="text-base text-gray-600 dark:text-gray-400">{error.message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const handleExport = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-white dark:bg-[#0a0a0a]">
      {/* Header */}
      <Header industry={data?.industry} onExport={handleExport} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-12">
        {data && (
          <div className="space-y-6 sm:space-y-12">
            {/* Hype Cycle Chart */}
            <HypeCycleChart
              technologies={data.technologies}
              onTechnologyClick={(techId) => setSelectedTechId(techId)}
            />

            {/* Knowledge Graph - Always visible */}
            <Card elevation="raised" padding="spacious">
              <CardHeader>
                <CardTitle as="h2">
                  {selectedTechId
                    ? `${data.technologies.find(t => t.id === selectedTechId)?.name} - Knowledge Graph`
                    : 'Full Knowledge Graph'}
                </CardTitle>
                <CardDescription>
                  {selectedTechId
                    ? 'Relationships and connections for this technology'
                    : 'All technologies and their interconnections'}
                </CardDescription>
              </CardHeader>
              <Neo4jGraphViz technologyId={selectedTechId} />
            </Card>

            {/* Selected Technology Detail */}
            {selectedTechId && (
              <Card elevation="elevated" padding="spacious" className="border-l-4 border-accent dark:border-accent-dark">
                <div className="flex items-center justify-between mb-6">
                  <CardTitle as="h2">
                    {data.technologies.find(t => t.id === selectedTechId)?.name} - Details
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedTechId(null)}
                    className="flex items-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Close
                  </Button>
                </div>

                {/* Technology Summary */}
                <div className="mb-8">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
                    <p className="text-base text-gray-700 dark:text-gray-300 leading-[1.7] mb-4">
                      {data.technologies.find(t => t.id === selectedTechId)?.summary}
                    </p>
                    <div className="flex items-center gap-8 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">Lifecycle Phase:</span>{' '}
                        <span className="text-base font-semibold text-gray-900 dark:text-white">
                          {data.technologies.find(t => t.id === selectedTechId)?.phase}
                        </span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">Confidence:</span>{' '}
                        <span className="text-base font-semibold text-accent dark:text-accent-dark">
                          {Math.round((data.technologies.find(t => t.id === selectedTechId)?.phase_confidence || 0) * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Raw Data (collapsible) */}
                <details className="mt-6">
                  <summary className="cursor-pointer text-base font-semibold text-gray-700 dark:text-gray-300 mb-3 hover:text-accent dark:hover:text-accent-dark transition-colors">
                    View Raw Data
                  </summary>
                  <pre className="text-sm bg-gray-100 dark:bg-gray-900 p-6 rounded-lg overflow-auto max-h-96 border border-gray-200 dark:border-gray-800">
                    {JSON.stringify(data.technologies.find(t => t.id === selectedTechId), null, 2)}
                  </pre>
                </details>
              </Card>
            )}

                  {/* Intelligence Foundation */}
            <Card elevation="raised" padding="spacious">
              <CardHeader>
                <CardTitle as="h2">Intelligence Foundation</CardTitle>
                <CardDescription>
                  Multi-source knowledge graph built from {data.metadata?.graph_data?.documents?.total?.toLocaleString() || 'N/A'} documents across 4 temporal intelligence layers
                </CardDescription>
              </CardHeader>

              {/* Key Metrics - Top Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {/* Documents Analyzed */}
                <div className="bg-gradient-to-br from-teal-50 to-white border border-teal-100 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <svg className="w-6 h-6 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm font-semibold text-teal-900 uppercase tracking-wide">Documents Analyzed</p>
                  </div>
                  <p className="text-5xl font-bold text-teal-700 mb-1">
                    {data.metadata?.graph_data?.documents?.total?.toLocaleString() || 'N/A'}
                  </p>
                  <p className="text-sm text-teal-600">Across 6 source types</p>
                </div>

                {/* Temporal Coverage */}
                <div className="bg-gradient-to-br from-blue-50 to-white border border-blue-100 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-sm font-semibold text-blue-900 uppercase tracking-wide">Temporal Coverage</p>
                  </div>
                  <p className="text-5xl font-bold text-blue-700 mb-1">
                    {data.metadata?.date_from && data.metadata?.date_to
                      ? `${Math.floor((new Date(data.metadata.date_to).getTime() - new Date(data.metadata.date_from).getTime()) / (365.25 * 24 * 60 * 60 * 1000))}+ yrs`
                      : 'N/A'}
                  </p>
                  <p className="text-sm text-blue-600">
                    {data.metadata?.date_from ? new Date(data.metadata.date_from).getFullYear() : 'N/A'} - {data.metadata?.date_to ? new Date(data.metadata.date_to).getFullYear() : 'N/A'}
                  </p>
                </div>

                {/* Knowledge Graph Scale */}
                <div className="bg-gradient-to-br from-purple-50 to-white border border-purple-100 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                    </svg>
                    <p className="text-sm font-semibold text-purple-900 uppercase tracking-wide">Knowledge Graph</p>
                  </div>
                  <p className="text-5xl font-bold text-purple-700 mb-1">
                    {data.metadata?.graph_data?.relationships?.total?.toLocaleString() || 'N/A'}
                  </p>
                  <p className="text-sm text-purple-600">
                    Relationships ({data.metadata?.graph_data?.companies?.total || 0} companies, {data.metadata?.graph_data?.technologies?.total?.toLocaleString() || 0} tech entities)
                  </p>
                </div>
              </div>

              {/* Document Sources & Phase Distribution - Bottom Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Document Sources Breakdown */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    Source Distribution
                  </h3>
                  <div className="space-y-3">
                    {data.metadata?.graph_data?.documents?.by_type && Object.entries(data.metadata.graph_data.documents.by_type)
                      .sort(([, a], [, b]) => (b as number) - (a as number))
                      .map(([type, count]) => {
                        const percentage = ((count as number) / (data.metadata?.graph_data?.documents?.total || 1) * 100).toFixed(1);
                        const typeLabels: Record<string, string> = {
                          patent: 'Patents',
                          technical_paper: 'Technical Papers',
                          sec_filing: 'SEC Filings',
                          news: 'News Articles',
                          government_contract: 'Gov Contracts',
                          github: 'GitHub Repos'
                        };
                        return (
                          <div key={type} className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1">
                              <div className="w-3 h-3 rounded-full" style={{
                                backgroundColor: {
                                  patent: '#64748b',
                                  technical_paper: '#94a3b8',
                                  sec_filing: '#475569',
                                  news: '#a8a29e',
                                  government_contract: '#57534e',
                                  github: '#78716c'
                                }[type] || '#8892a6'
                              }}></div>
                              <span className="text-sm font-medium text-gray-700 flex-1">{typeLabels[type] || type}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="w-32 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-teal-600 h-2 rounded-full transition-all duration-500"
                                  style={{ width: `${percentage}%` }}
                                ></div>
                              </div>
                              <span className="text-sm font-bold text-gray-900 w-16 text-right">{(count as number).toLocaleString()}</span>
                              <span className="text-xs text-gray-500 w-12 text-right">{percentage}%</span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* Phase Distribution */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    Lifecycle Phase Distribution
                  </h3>
                  <div className="space-y-3">
                    {data.metadata?.phases && Object.entries(data.metadata.phases).map(([phase, count]) => {
                      const phaseLabels: Record<string, string> = {
                        innovation_trigger: 'Innovation Trigger',
                        peak: 'Peak of Expectations',
                        trough: 'Trough of Disillusionment',
                        slope: 'Slope of Enlightenment',
                        plateau: 'Plateau of Productivity'
                      };
                      const phaseColors: Record<string, string> = {
                        innovation_trigger: '#4169E1',
                        peak: '#DC143C',
                        trough: '#FF8C00',
                        slope: '#20B2AA',
                        plateau: '#9370DB'
                      };
                      const countNum = (count as number) || 0;
                      const percentage = (countNum / (data.metadata?.total_count || 1) * 100).toFixed(0);
                      return (
                        <div key={phase} className="flex items-center gap-3">
                          <div
                            className="w-3 h-3 rounded-full shadow-sm"
                            style={{ backgroundColor: phaseColors[phase] || '#8892a6' }}
                          ></div>
                          <span className="text-sm font-medium text-gray-700 flex-1">{phaseLabels[phase] || phase}</span>
                          <span className="text-xs text-gray-500">{percentage}%</span>
                        </div>
                      );
                    })}
                  </div>
                  {/* Hidden for now - Total Technologies section
                  <div className="mt-6 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Total Technologies Analyzed:</span>
                      <span className="font-bold text-teal-700 text-lg">{data.metadata?.total_count || data.technologies.length}</span>
                    </div>
                    {data.metadata?.normalization_config && (
                      <div className="mt-2 text-xs text-gray-500">
                        Filtered from {data.metadata.normalization_config.original_count} candidates (top {data.metadata.normalization_config.top_n_per_phase} per phase)
                      </div>
                    )}
                  </div>
                  */}
                </div>
              </div>

              {/* Analysis Timestamp */}
              <div className="mt-8 pt-6 border-t border-gray-200 flex items-center justify-between text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Analysis Generated: {new Date(data.generated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-teal-100 text-teal-700 rounded text-xs font-semibold">Multi-Source Intelligence</span>
                </div>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
