/**
 * RunHistory - Pipeline run history selector component
 *
 * Features:
 * - Dropdown list of pipeline runs (newest first)
 * - Shows run metadata (date, tech count, duration)
 * - Delete run action
 * - Select run to view chart
 */

import React from 'react'
import { useRunHistory, RunMetadata } from '../../hooks/useRunHistory'

interface RunHistoryProps {
  onRunSelect?: (runId: string) => void
}

export function RunHistory({ onRunSelect }: RunHistoryProps) {
  const {
    runs,
    runCount,
    isLoadingRuns,
    selectedRunId,
    selectRun,
    deleteRun,
    isDeleting,
  } = useRunHistory()

  const handleSelect = (runId: string) => {
    selectRun(runId)
    if (onRunSelect) {
      onRunSelect(runId)
    }
  }

  const handleDelete = (e: React.MouseEvent, runId: string) => {
    e.stopPropagation()

    if (window.confirm('Are you sure you want to delete this run?')) {
      deleteRun(runId)
    }
  }

  const formatDate = (isoDate: string) => {
    const date = new Date(isoDate)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  if (isLoadingRuns) {
    return (
      <div className="p-3 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-[#0f766e] rounded-full animate-spin" />
          Loading run history...
        </div>
      </div>
    )
  }

  if (runCount === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
        No pipeline runs yet. Run the pipeline to create history.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Run History</h3>
          <div className="text-xs text-gray-600">{runCount} runs</div>
        </div>
      </div>

      {/* Run list */}
      <div className="max-h-96 overflow-y-auto">
        {runs.map((run) => (
          <div
            key={run.run_id}
            className={`
              px-4 py-3 border-b border-gray-100 cursor-pointer transition-colors
              ${
                selectedRunId === run.run_id
                  ? 'bg-teal-50 border-l-4 border-l-[#0f766e]'
                  : 'hover:bg-gray-50'
              }
            `}
            onClick={() => handleSelect(run.run_id)}
          >
            <div className="flex items-start justify-between gap-3">
              {/* Run info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {formatDate(run.created_at)}
                  </div>
                  {selectedRunId === run.run_id && (
                    <div className="px-2 py-0.5 text-xs font-medium text-teal-700 bg-teal-100 rounded">
                      Active
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-gray-600">
                  <div className="flex items-center gap-1">
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                      />
                    </svg>
                    {run.tech_count} techs
                  </div>

                  <div className="flex items-center gap-1">
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    {formatDuration(run.duration_seconds)}
                  </div>

                  <div className="text-gray-500">{run.config.community_version}</div>
                </div>
              </div>

              {/* Delete button */}
              <button
                onClick={(e) => handleDelete(e, run.run_id)}
                disabled={isDeleting}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                title="Delete run"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
