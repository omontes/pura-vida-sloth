/**
 * useRunHistory - Hook for managing pipeline run history
 *
 * Features:
 * - List all pipeline runs (newest first)
 * - Select and load specific runs
 * - Delete runs
 * - React Query caching for performance
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

export interface RunMetadata {
  run_id: string
  created_at: string
  config: {
    tech_count: number
    community_version: string
    enable_tavily: boolean
    min_docs: number
    verbosity: string
  }
  duration_seconds: number
  tech_count: number
  phases: string[]
}

export interface RunData {
  run_id: string
  chart_data: any
  metadata: RunMetadata
  original_chart?: any
}

interface RunListResponse {
  runs: RunMetadata[]
  count: number
}

/**
 * Hook for managing pipeline run history
 */
export function useRunHistory() {
  const queryClient = useQueryClient()
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)

  // Get API URL from environment (supports both dev and production)
  const API_URL = import.meta.env.VITE_API_URL || '';

  // Query: List all runs
  const {
    data: runList,
    isLoading: isLoadingRuns,
    error: runsError,
  } = useQuery<RunListResponse>({
    queryKey: ['pipelineRuns'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/pipeline/runs?limit=20`)
      if (!response.ok) {
        throw new Error('Failed to fetch runs')
      }
      return response.json()
    },
    refetchOnWindowFocus: false,
  })

  // Query: Get specific run data
  const {
    data: selectedRun,
    isLoading: isLoadingRun,
    error: runError,
  } = useQuery<RunData>({
    queryKey: ['pipelineRun', selectedRunId],
    queryFn: async () => {
      if (!selectedRunId) {
        throw new Error('No run selected')
      }
      const response = await fetch(`${API_URL}/api/pipeline/runs/${selectedRunId}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch run ${selectedRunId}`)
      }
      return response.json()
    },
    enabled: selectedRunId !== null,
    refetchOnWindowFocus: false,
  })

  // Mutation: Delete run
  const deleteRunMutation = useMutation({
    mutationFn: async (runId: string) => {
      const response = await fetch(`${API_URL}/api/pipeline/runs/${runId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(`Failed to delete run ${runId}`)
      }
      return response.json()
    },
    onSuccess: (_, runId) => {
      // Invalidate runs list to refresh
      queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] })

      // If deleted run was selected, clear selection
      if (selectedRunId === runId) {
        setSelectedRunId(null)
      }
    },
  })

  return {
    // Run list
    runs: runList?.runs || [],
    runCount: runList?.count || 0,
    isLoadingRuns,
    runsError,

    // Selected run
    selectedRunId,
    selectedRun,
    isLoadingRun,
    runError,

    // Actions
    selectRun: setSelectedRunId,
    deleteRun: (runId: string) => deleteRunMutation.mutate(runId),
    isDeleting: deleteRunMutation.isPending,

    // Refresh
    refreshRuns: () => queryClient.invalidateQueries({ queryKey: ['pipelineRuns'] }),
  }
}
