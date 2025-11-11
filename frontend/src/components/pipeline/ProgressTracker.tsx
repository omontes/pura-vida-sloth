/**
 * ProgressTracker - Visual progress indicator for pipeline execution.
 *
 * Features:
 * - Overall progress bar
 * - Current agent display
 * - Technology counter
 * - Duration timer
 * - Agent checklist with status icons
 */

import React, { useEffect, useState } from 'react'
import { AgentStatus, getAgentDisplayName } from '../../types/pipeline'

interface ProgressTrackerProps {
  progress: number
  currentAgent?: string
  currentTech?: string
  techCount?: number
  totalTechs?: number
  agents: AgentStatus[]
  startTime?: number
}

export function ProgressTracker({
  progress,
  currentAgent,
  currentTech,
  techCount,
  totalTechs,
  agents,
  startTime,
}: ProgressTrackerProps) {
  const [elapsedTime, setElapsedTime] = useState(0)

  // Update elapsed time every second
  useEffect(() => {
    if (!startTime) return

    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [startTime])

  // Format duration as MM:SS
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Get status icon for agent
  const getStatusIcon = (status: AgentStatus['status']): string => {
    switch (status) {
      case 'completed':
        return '✓'
      case 'active':
        return '⟳'
      case 'error':
        return '✗'
      case 'pending':
      default:
        return '○'
    }
  }

  // Get status color for agent
  const getStatusColor = (status: AgentStatus['status']): string => {
    switch (status) {
      case 'completed':
        return 'text-green-600'
      case 'active':
        return 'text-blue-600 animate-spin'
      case 'error':
        return 'text-red-600'
      case 'pending':
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className="space-y-4">
      {/* Overall progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Overall Progress</span>
          <span className="text-gray-600">{progress}%</span>
        </div>
        <div className="h-2.5 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Current status */}
      <div className="grid grid-cols-3 gap-4 py-3 px-4 bg-gray-50 rounded-lg border border-gray-200">
        {/* Current agent */}
        <div className="space-y-1">
          <div className="text-xs text-gray-600 uppercase tracking-wide">Current Agent</div>
          <div className="text-sm font-medium text-gray-900">
            {currentAgent ? getAgentDisplayName(currentAgent) : 'Initializing...'}
          </div>
        </div>

        {/* Technology count */}
        <div className="space-y-1">
          <div className="text-xs text-gray-600 uppercase tracking-wide">Technologies</div>
          <div className="text-sm font-medium text-gray-900">
            {techCount !== undefined && totalTechs !== undefined
              ? `${techCount} / ${totalTechs}`
              : '-'}
          </div>
        </div>

        {/* Duration */}
        <div className="space-y-1">
          <div className="text-xs text-gray-600 uppercase tracking-wide">Duration</div>
          <div className="text-sm font-medium text-gray-900 font-mono">
            {startTime ? formatDuration(elapsedTime) : '00:00'}
          </div>
        </div>
      </div>

      {/* Current technology */}
      {currentTech && (
        <div className="py-2 px-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-xs text-blue-600 mb-1">Processing</div>
          <div className="text-sm text-gray-900 font-medium">
            {currentTech.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
          </div>
        </div>
      )}

      {/* Agent checklist */}
      <div className="space-y-2">
        <div className="text-xs text-gray-600 uppercase tracking-wide">Agent Pipeline</div>
        <div className="max-h-60 overflow-y-auto pr-2 space-y-1">
          {agents.map((agent) => {
            const isActive = agent.status === 'active'
            const duration =
              agent.start_time && agent.end_time
                ? ((agent.end_time - agent.start_time) / 1000).toFixed(1)
                : null

            return (
              <div
                key={agent.name}
                className={`flex items-center gap-3 py-2 px-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-blue-50 border border-blue-200'
                    : 'bg-gray-50 border border-transparent'
                }`}
              >
                {/* Status icon */}
                <span className={`text-lg ${getStatusColor(agent.status)}`}>
                  {getStatusIcon(agent.status)}
                </span>

                {/* Agent name */}
                <span
                  className={`flex-1 text-sm ${
                    isActive ? 'text-blue-700 font-medium' : 'text-gray-600'
                  }`}
                >
                  {agent.display_name}
                </span>

                {/* Duration */}
                {duration && (
                  <span className="text-xs text-gray-600 font-mono">{duration}s</span>
                )}

                {/* Error indicator */}
                {agent.error && (
                  <span className="text-xs text-red-600" title={agent.error}>
                    ⚠
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
