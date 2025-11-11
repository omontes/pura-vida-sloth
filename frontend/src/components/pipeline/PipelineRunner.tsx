/**
 * PipelineRunner - Main modal component for multi-agent pipeline execution.
 *
 * Features:
 * - Configuration → Running → Completed workflow
 * - Real-time progress tracking
 * - Live log streaming
 * - Professional C-level UI
 * - Automatic chart updates
 */

import React, { useEffect, useState, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usePipelineWebSocket } from '../../hooks/usePipelineWebSocket'
import { PipelineConfig } from '../../types/pipeline'
import { ConfigForm } from './ConfigForm'
import { ProgressTracker } from './ProgressTracker'
import { LogViewer } from './LogViewer'

interface PipelineRunnerProps {
  isOpen: boolean
  onClose: () => void
  onComplete?: (techCount?: number) => void
}

export function PipelineRunner({ isOpen, onClose, onComplete }: PipelineRunnerProps) {
  const { state, connectionState, connect, disconnect, reset, error } = usePipelineWebSocket()
  const queryClient = useQueryClient()
  const [startTime, setStartTime] = useState<number | undefined>()
  const completionHandledRef = useRef(false)

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      reset()
    }
  }, [isOpen, reset])

  // Handle pipeline start
  const handleStart = (config: PipelineConfig) => {
    setStartTime(Date.now())
    completionHandledRef.current = false // Reset completion flag
    connect(config)
  }

  // Handle pipeline completion (only once per completion)
  useEffect(() => {
    if (state.stage === 'completed' && state.chart_data && !completionHandledRef.current) {
      completionHandledRef.current = true

      // Invalidate React Query cache to trigger chart refetch
      queryClient.invalidateQueries({ queryKey: ['hypeCycleData'] })

      // Notify parent component with technology count
      if (onComplete) {
        onComplete(state.chart_data.technologies.length)
      }
    }

    // Reset flag when stage changes away from completed
    if (state.stage !== 'completed') {
      completionHandledRef.current = false
    }
  }, [state.stage, state.chart_data, queryClient, onComplete])

  // Handle close
  const handleClose = () => {
    if (state.stage === 'running') {
      const confirmClose = window.confirm(
        'Pipeline is currently running. Are you sure you want to close? This will not stop the pipeline.'
      )
      if (!confirmClose) return
    }

    disconnect()
    onClose()
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-white rounded-xl shadow-2xl border border-gray-200 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto animate-in fade-in slide-in-from-bottom-4 duration-300"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Multi-Agent Hype Cycle Analysis
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {state.stage === 'config' && 'Configure and launch pipeline execution'}
                {state.stage === 'running' &&
                  `Processing ${state.config?.tech_count || 0} technologies`}
                {state.stage === 'completed' && 'Analysis completed successfully'}
                {state.stage === 'error' && 'Pipeline execution failed'}
              </p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-600 hover:text-gray-900 transition-colors p-2 hover:bg-gray-100 rounded-lg"
              title="Close"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Configuration Stage */}
            {state.stage === 'config' && (
              <div className="max-w-2xl mx-auto">
                <div className="mb-6 p-4 bg-teal-50 border border-teal-200 rounded-lg">
                  <div className="flex items-start gap-3">
                    <svg
                      className="w-5 h-5 text-[#0f766e] mt-0.5 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <div className="flex-1 text-sm text-teal-900">
                      <p className="font-medium mb-1">About This Pipeline</p>
                      <p className="text-teal-800">
                        The multi-agent system will analyze technologies through 12 specialized
                        agents, scoring each across 4 intelligence layers (Innovation, Adoption,
                        Narrative, Risk) to determine precise hype cycle positioning.
                      </p>
                    </div>
                  </div>
                </div>

                <ConfigForm
                  onSubmit={handleStart}
                  onCancel={onClose}
                  disabled={connectionState === 'connecting'}
                />

                {error && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}
              </div>
            )}

            {/* Running Stage */}
            {state.stage === 'running' && (
              <div className="space-y-6">
                <ProgressTracker
                  progress={state.progress}
                  currentAgent={state.current_agent}
                  currentTech={state.current_tech}
                  techCount={state.technologies.filter((t) => t.status === 'completed').length}
                  totalTechs={state.config?.tech_count}
                  agents={state.agents}
                  startTime={startTime}
                />

                <LogViewer logs={state.logs} maxHeight={300} />
              </div>
            )}

            {/* Completed Stage */}
            {state.stage === 'completed' && (
              <div className="max-w-2xl mx-auto space-y-6">
                {/* Success message */}
                <div className="p-6 bg-green-50 border border-green-200 rounded-lg text-center">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-4">
                    <svg
                      className="w-10 h-10 text-green-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-bold text-green-900 mb-2">
                    Analysis Completed Successfully
                  </h3>
                  <p className="text-green-800 mb-4">
                    Analyzed {state.config?.tech_count || 0} technologies in{' '}
                    {state.duration_seconds
                      ? `${Math.round(state.duration_seconds)}s`
                      : 'unknown time'}
                  </p>
                  <p className="text-sm text-green-700">
                    The hype cycle chart has been updated with the latest results
                  </p>
                </div>

                {/* Summary */}
                {state.chart_data && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="text-sm text-gray-600 mb-1">Total Technologies (Top 10 / Phase)</div>
                      <div className="text-2xl font-semibold text-gray-900">
                        {state.chart_data.technologies.length}
                      </div>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="text-sm text-gray-600 mb-1">Phases Covered</div>
                      <div className="text-2xl font-semibold text-gray-900">
                        {Object.keys(state.chart_data.metadata?.phases || {}).length}
                      </div>
                    </div>
                  </div>
                )}

                {/* Logs (collapsible) */}
                <details className="group">
                  <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900 transition-colors">
                    View execution logs ({state.logs.length} entries)
                  </summary>
                  <div className="mt-3">
                    <LogViewer logs={state.logs} maxHeight={200} />
                  </div>
                </details>
              </div>
            )}

            {/* Error Stage */}
            {state.stage === 'error' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                    <svg
                      className="w-8 h-8 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-red-900 mb-2">Pipeline Failed</h3>
                  <p className="text-red-800 mb-4">{state.error || error}</p>
                  <p className="text-sm text-red-700">
                    Check the logs below for more details
                  </p>
                </div>

                <LogViewer logs={state.logs} maxHeight={300} />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
            {state.stage === 'config' && (
              <p className="text-xs text-gray-600 mr-auto">
                Tip: Start with 10-20 technologies to test the pipeline
              </p>
            )}

            {state.stage === 'running' && (
              <p className="text-xs text-gray-600 mr-auto">
                Pipeline is running in background. Feel free to close this modal.
              </p>
            )}

            {state.stage === 'completed' && (
              <button
                onClick={() => {
                  onClose()
                  // The chart should already be updated via React Query invalidation
                }}
                className="px-5 py-2.5 text-sm font-medium text-white bg-[#0f766e] rounded-lg hover:bg-[#0d9488] focus:outline-none focus:ring-2 focus:ring-[#0f766e] transition-colors"
              >
                View Updated Chart
              </button>
            )}

            {(state.stage === 'error' || state.stage === 'completed') && (
              <button
                onClick={onClose}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 transition-colors"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
