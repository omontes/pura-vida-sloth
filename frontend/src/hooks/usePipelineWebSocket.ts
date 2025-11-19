/**
 * usePipelineWebSocket - Custom hook for managing pipeline WebSocket connection.
 *
 * Handles connection lifecycle, event streaming, and reconnection logic.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  PipelineConfig,
  AnyPipelineEvent,
  PipelineRunnerState,
  getInitialAgentStatuses,
  AgentStatus,
  TechnologyProgress,
} from '../types/pipeline'

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

interface UsePipelineWebSocketReturn {
  state: PipelineRunnerState
  connectionState: ConnectionState
  connect: (config: PipelineConfig) => void
  disconnect: () => void
  reset: () => void
  error: string | null
}

/**
 * Custom hook for pipeline WebSocket connection
 */
export function usePipelineWebSocket(): UsePipelineWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [error, setError] = useState<string | null>(null)
  const [state, setState] = useState<PipelineRunnerState>({
    stage: 'config',
    progress: 0,
    agents: getInitialAgentStatuses(),
    technologies: [],
    logs: [],
  })

  // Handle incoming WebSocket events
  const handleEvent = useCallback((event: AnyPipelineEvent) => {
    switch (event.type) {
      case 'pipeline_start':
        setState((prev) => ({
          ...prev,
          stage: 'running',
          config: event.config,
          progress: 0,
          agents: getInitialAgentStatuses(),
          technologies: [],
          logs: [],
          error: undefined,
        }))
        break

      case 'agent_start':
        setState((prev) => {
          const agents = prev.agents.map((agent) =>
            agent.name === event.agent_name
              ? { ...agent, status: 'active' as const, start_time: Date.now() }
              : agent
          )
          return {
            ...prev,
            current_agent: event.agent_name,
            current_tech: event.tech_id,
            agents,
          }
        })
        break

      case 'agent_complete':
        setState((prev) => {
          const agents = prev.agents.map((agent) =>
            agent.name === event.agent_name
              ? { ...agent, status: 'completed' as const, end_time: Date.now() }
              : agent
          )
          return { ...prev, agents }
        })
        break

      case 'tech_complete':
        setState((prev) => {
          // Update or add technology progress
          const existingIndex = prev.technologies.findIndex(
            (t) => t.tech_id === event.tech_id
          )

          let technologies: TechnologyProgress[]
          if (existingIndex >= 0) {
            technologies = [...prev.technologies]
            technologies[existingIndex] = {
              ...technologies[existingIndex],
              status: 'completed',
              phase: event.phase,
            }
          } else {
            technologies = [
              ...prev.technologies,
              {
                tech_id: event.tech_id,
                tech_name: event.tech_name,
                status: 'completed',
                phase: event.phase,
              },
            ]
          }

          return {
            ...prev,
            technologies,
            progress: Math.round((event.progress / event.total) * 100),
          }
        })
        break

      case 'pipeline_progress':
        setState((prev) => ({
          ...prev,
          progress: event.progress,
          current_tech: event.current_tech || prev.current_tech,
          current_agent: event.current_agent || prev.current_agent,
        }))
        break

      case 'pipeline_complete':
        setState((prev) => ({
          ...prev,
          stage: 'completed',
          progress: 100,
          chart_data: event.chart_data,
          duration_seconds: event.duration_seconds,
        }))
        setConnectionState('disconnected')
        break

      case 'pipeline_error':
        setState((prev) => ({
          ...prev,
          stage: 'error',
          error: event.error,
        }))
        setError(event.error)
        setConnectionState('error')
        break

      case 'pipeline_log':
        setState((prev) => ({
          ...prev,
          logs: [...prev.logs, event],
        }))
        break
    }
  }, [])

  // Connect to WebSocket
  const connect = useCallback(
    (config: PipelineConfig) => {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close()
      }

      setConnectionState('connecting')
      setError(null)

      // IMMEDIATE FEEDBACK: Transition to running state with initial log
      setState((prev) => ({
        ...prev,
        stage: 'running',
        config,
        progress: 0,
        agents: getInitialAgentStatuses(),
        technologies: [],
        logs: [
          {
            type: 'pipeline_log' as const,
            level: 'info' as const,
            message: 'Connecting to pipeline service...',
            timestamp: new Date().toISOString(),
          },
        ],
        error: undefined,
      }))

      // Determine WebSocket URL
      // In development: use current host (Vite proxy handles routing)
      // In production: use backend API URL from environment
      const apiUrl = import.meta.env.VITE_API_URL;

      let wsUrl: string;
      if (apiUrl && apiUrl.startsWith('http')) {
        // Production: convert HTTP(S) URL to WS(S) URL
        const wsProtocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:';
        const apiHost = apiUrl.replace(/^https?:\/\//, '');
        wsUrl = `${wsProtocol}//${apiHost}/api/pipeline/ws/run`;
      } else {
        // Development: use current host
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = `${protocol}//${host}/api/pipeline/ws/run`;
      }

      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('[Pipeline] WebSocket connected')
          setConnectionState('connected')

          // Add connection success log
          setState((prev) => ({
            ...prev,
            logs: [
              ...prev.logs,
              {
                type: 'pipeline_log' as const,
                level: 'info' as const,
                message: 'Connected to pipeline service',
                timestamp: new Date().toISOString(),
              },
              {
                type: 'pipeline_log' as const,
                level: 'info' as const,
                message: `Starting analysis of ${config.tech_count} technologies...`,
                timestamp: new Date().toISOString(),
              },
            ],
          }))

          // Send configuration
          ws.send(JSON.stringify(config))
        }

        ws.onmessage = (messageEvent) => {
          try {
            const event = JSON.parse(messageEvent.data) as AnyPipelineEvent
            console.log('[Pipeline] Event received:', event.type)
            handleEvent(event)
          } catch (err) {
            console.error('[Pipeline] Failed to parse event:', err)
          }
        }

        ws.onerror = (errorEvent) => {
          console.error('[Pipeline] WebSocket error:', errorEvent)
          setConnectionState('error')
          setError('WebSocket connection error')

          // Add error log
          setState((prev) => ({
            ...prev,
            logs: [
              ...prev.logs,
              {
                type: 'pipeline_log' as const,
                level: 'error' as const,
                message: 'Connection error occurred',
                timestamp: new Date().toISOString(),
              },
            ],
          }))
        }

        ws.onclose = (closeEvent) => {
          console.log('[Pipeline] WebSocket closed:', closeEvent.code, closeEvent.reason)
          setConnectionState('disconnected')

          // If closed unexpectedly, set error
          if (closeEvent.code !== 1000 && closeEvent.code !== 1001) {
            setError(`Connection closed unexpectedly (code: ${closeEvent.code})`)

            // Add close log
            setState((prev) => ({
              ...prev,
              logs: [
                ...prev.logs,
                {
                  type: 'pipeline_log' as const,
                  level: 'warning' as const,
                  message: `Connection closed unexpectedly (code: ${closeEvent.code})`,
                  timestamp: new Date().toISOString(),
                },
              ],
            }))
          }
        }
      } catch (err) {
        console.error('[Pipeline] Failed to create WebSocket:', err)
        setConnectionState('error')
        setError('Failed to create WebSocket connection')

        // Add error log
        setState((prev) => ({
          ...prev,
          stage: 'error',
          error: 'Failed to create WebSocket connection',
          logs: [
            ...prev.logs,
            {
              type: 'pipeline_log' as const,
              level: 'error' as const,
              message: 'Failed to create WebSocket connection',
              timestamp: new Date().toISOString(),
            },
          ],
        }))
      }
    },
    [handleEvent]
  )

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User requested disconnect')
      wsRef.current = null
    }
    setConnectionState('disconnected')
  }, [])

  // Reset state to initial config stage
  const reset = useCallback(() => {
    setState({
      stage: 'config',
      progress: 0,
      agents: getInitialAgentStatuses(),
      technologies: [],
      logs: [],
    })
    setError(null)
    setConnectionState('disconnected')
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return {
    state,
    connectionState,
    connect,
    disconnect,
    reset,
    error,
  }
}
