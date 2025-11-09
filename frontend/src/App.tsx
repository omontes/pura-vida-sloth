import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Header from './components/layout/Header'
import HypeCycleChart from './components/charts/HypeCycleChart'
import Neo4jGraphViz from './components/graph/Neo4jGraphViz'
import Card, { CardHeader, CardTitle, CardDescription } from './components/ui/Card'
import Button from './components/ui/Button'
import type { HypeCycleChartData } from './types/hypeCycle'

function App() {
  const [selectedTechId, setSelectedTechId] = useState<string | null>(null)

  // Fetch hype cycle data from mock JSON
  const { data, isLoading, error } = useQuery<HypeCycleChartData>({
    queryKey: ['hypeCycleData'],
    queryFn: async () => {
      const response = await fetch('/mock-data/hype_cycle_chart.json')
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
            <p className="text-2xl font-bold mb-3">Error Loading Data</p>
            <p className="text-base text-gray-600 dark:text-gray-400">{error.message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const handleExport = () => {
    console.log('Export functionality to be implemented');
    // TODO: Implement PDF/JSON export
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

      

            {/* Selected Technology Detail */}
            {selectedTechId && (
              <Card elevation="elevated" padding="spacious" className="border-l-4 border-accent dark:border-accent-dark">
                <div className="flex items-center justify-between mb-6">
                  <CardTitle as="h2">
                    {data.technologies.find(t => t.id === selectedTechId)?.name}
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
                    <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
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

                {/* Neo4j Graph Visualization */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                    Knowledge Graph
                  </h3>
                  <Neo4jGraphViz technologyId={selectedTechId} />
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

                  {/* Metadata */}
            <Card elevation="raised" padding="spacious">
              <CardHeader>
                <CardTitle as="h2">Analysis Metadata</CardTitle>
                <CardDescription>
                  Multi-source intelligence analysis across 4 temporal layers
                </CardDescription>
              </CardHeader>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Documents Analyzed</p>
                  <p className="text-4xl font-bold text-gray-900 dark:text-white">
                    {data.metadata.total_documents.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Date Range</p>
                  <p className="text-xl font-semibold text-gray-900 dark:text-white">
                    {data.metadata.date_range}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Generated</p>
                  <p className="text-xl font-semibold text-gray-900 dark:text-white">
                    {new Date(data.generated_at).toLocaleDateString()}
                  </p>
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
