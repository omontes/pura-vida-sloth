/**
 * LogViewer - Console-style log viewer for pipeline execution.
 *
 * Features:
 * - Color-coded by log level
 * - Auto-scroll with lock/unlock
 * - Export logs functionality
 * - Professional monospace styling
 */

import React, { useEffect, useRef, useState } from 'react'
import { PipelineLogEvent } from '../../types/pipeline'

interface LogViewerProps {
  logs: PipelineLogEvent[]
  maxHeight?: number
}

/**
 * Convert UTC timestamp to UTC-6 (Central Standard Time)
 */
function formatTimestampUTC6(isoTimestamp: string): string {
  const date = new Date(isoTimestamp)

  // Convert to UTC-6 (subtract 6 hours)
  const utc6Date = new Date(date.getTime() - 6 * 60 * 60 * 1000)

  // Format as HH:MM:SS
  return utc6Date.toISOString().substring(11, 19)
}

export function LogViewer({ logs, maxHeight = 400 }: LogViewerProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10

    setAutoScroll(isAtBottom)
  }

  // Export logs to text file
  const handleExportLogs = () => {
    const logText = logs
      .map((log) => {
        const timestamp = formatTimestampUTC6(log.timestamp)
        return `[${timestamp} UTC-6] [${log.level.toUpperCase()}] ${log.message}`
      })
      .join('\n')

    const blob = new Blob([logText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pipeline-logs-${new Date().toISOString()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Get color based on log level
  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'error':
        return 'text-red-700'
      case 'warning':
        return 'text-yellow-700'
      case 'debug':
        return 'text-gray-500'
      case 'info':
      default:
        return 'text-gray-700'
    }
  }

  // Get level badge style
  const getLevelBadge = (level: string): string => {
    switch (level) {
      case 'error':
        return 'bg-red-100 text-red-700 border-red-300'
      case 'warning':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300'
      case 'debug':
        return 'bg-gray-100 text-gray-600 border-gray-300'
      case 'info':
      default:
        return 'bg-blue-100 text-blue-700 border-blue-300'
    }
  }

  if (logs.length === 0) {
    return (
      <div
        className="rounded-lg border border-gray-300 bg-gray-50 p-6 text-center"
        style={{ maxHeight }}
      >
        <p className="text-gray-600 text-sm">
          Waiting for pipeline execution to begin...
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-700">Pipeline Logs</h3>
          <span className="text-xs text-gray-600">
            {logs.length} {logs.length === 1 ? 'entry' : 'entries'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className="text-xs text-gray-600 hover:text-gray-900 transition-colors"
            title={autoScroll ? 'Disable auto-scroll' : 'Enable auto-scroll'}
          >
            {autoScroll ? '🔓 Auto-scroll' : '🔒 Scroll locked'}
          </button>

          {/* Export button */}
          <button
            onClick={handleExportLogs}
            className="text-xs text-blue-600 hover:text-blue-700 transition-colors"
            title="Export logs to file"
          >
            ⬇️ Export
          </button>
        </div>
      </div>

      {/* Log container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="rounded-lg border border-gray-300 bg-white p-4 overflow-y-auto font-mono text-xs"
        style={{ maxHeight }}
      >
        <div className="space-y-1">
          {logs.map((log, index) => {
            const timestamp = formatTimestampUTC6(log.timestamp)

            return (
              <div
                key={index}
                className="flex items-start gap-3 py-1 hover:bg-gray-50 transition-colors"
              >
                {/* Timestamp */}
                <span className="text-gray-500 select-none shrink-0" title="UTC-6">{timestamp}</span>

                {/* Level badge */}
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase border shrink-0 ${getLevelBadge(
                    log.level
                  )}`}
                >
                  {log.level}
                </span>

                {/* Message */}
                <span className={`flex-1 ${getLevelColor(log.level)}`}>
                  {log.message}
                </span>
              </div>
            )
          })}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}
