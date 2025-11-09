import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Header from './components/layout/Header'
import HypeCycleChart from './components/charts/HypeCycleChart'
import Neo4jGraphViz from './components/graph/Neo4jGraphViz'
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
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading Hype Cycle data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">Error loading data</p>
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    )
  }

  const handleExport = () => {
    console.log('Export functionality to be implemented');
    // TODO: Implement PDF/JSON export
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header with theme toggle */}
      <Header industry={data?.industry} onExport={handleExport} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {data && (
          <div className="space-y-8">
            {/* Hype Cycle Chart */}
            <HypeCycleChart
              technologies={data.technologies}
              onTechnologyClick={(techId) => setSelectedTechId(techId)}
            />

            {/* Metadata */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Analysis Metadata
              </h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Documents Analyzed</p>
                  <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {data.metadata.total_documents.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Date Range</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {data.metadata.date_range}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Generated</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {new Date(data.generated_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Selected Technology Detail */}
            {selectedTechId && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {data.technologies.find(t => t.id === selectedTechId)?.name}
                  </h3>
                  <button
                    onClick={() => setSelectedTechId(null)}
                    className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    ✕ Close
                  </button>
                </div>

                {/* Technology Summary */}
                <div className="mb-6">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                      {data.technologies.find(t => t.id === selectedTechId)?.summary}
                    </p>
                    <div className="flex items-center gap-4 mt-4 text-xs">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Phase:</span>{' '}
                        <span className="font-semibold">
                          {data.technologies.find(t => t.id === selectedTechId)?.phase}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Confidence:</span>{' '}
                        <span className="font-semibold">
                          {(data.technologies.find(t => t.id === selectedTechId)?.phase_confidence || 0) * 100}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Neo4j Graph Visualization */}
                <div className="mb-6">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Knowledge Graph
                  </h4>
                  <Neo4jGraphViz technologyId={selectedTechId} />
                </div>

                {/* Raw Data (collapsible) */}
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    View Raw Data
                  </summary>
                  <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-4 rounded overflow-auto max-h-96">
                    {JSON.stringify(data.technologies.find(t => t.id === selectedTechId), null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
