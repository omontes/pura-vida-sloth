/**
 * Pipeline Types - TypeScript interfaces for multi-agent pipeline execution.
 *
 * Matches backend schemas in src/api/models/pipeline_schemas.py
 */

import { HypeCycleChartData } from './hypeCycle'

export type CommunityVersion = 'v0' | 'v1' | 'v2'
export type VerbosityLevel = 'normal' | 'verbose' | 'debug'
export type PipelineEventType =
  | 'pipeline_start'
  | 'agent_start'
  | 'agent_complete'
  | 'tech_complete'
  | 'pipeline_progress'
  | 'pipeline_complete'
  | 'pipeline_error'
  | 'pipeline_log'

export type LogLevel = 'debug' | 'info' | 'warning' | 'error'

/**
 * Configuration for pipeline execution
 */
export interface PipelineConfig {
  tech_count: number // 1-200
  community_version: CommunityVersion
  enable_tavily: boolean
  min_docs: number // 1-20
  verbosity: VerbosityLevel
}

/**
 * Base interface for all pipeline events
 */
export interface PipelineEvent {
  type: PipelineEventType
  timestamp: string
  message?: string
}

/**
 * Event emitted when pipeline execution begins
 */
export interface PipelineStartEvent extends PipelineEvent {
  type: 'pipeline_start'
  config: PipelineConfig
}

/**
 * Event emitted when an agent begins processing
 */
export interface AgentStartEvent extends PipelineEvent {
  type: 'agent_start'
  agent_name: string
  tech_id?: string
  tech_name?: string
}

/**
 * Event emitted when an agent completes processing
 */
export interface AgentCompleteEvent extends PipelineEvent {
  type: 'agent_complete'
  agent_name: string
  tech_id?: string
  duration_seconds?: number
}

/**
 * Event emitted when a technology completes all agent processing
 */
export interface TechCompleteEvent extends PipelineEvent {
  type: 'tech_complete'
  tech_id: string
  tech_name: string
  progress: number
  total: number
  phase?: string
}

/**
 * Event emitted for general progress updates
 */
export interface PipelineProgressEvent extends PipelineEvent {
  type: 'pipeline_progress'
  progress: number // 0-100
  current_tech?: string
  current_agent?: string
}

/**
 * Event emitted when pipeline execution completes successfully
 */
export interface PipelineCompleteEvent extends PipelineEvent {
  type: 'pipeline_complete'
  chart_data: HypeCycleChartData
  tech_count: number
  duration_seconds: number
  output_file: string
}

/**
 * Event emitted when an error occurs during pipeline execution
 */
export interface PipelineErrorEvent extends PipelineEvent {
  type: 'pipeline_error'
  error: string
  tech_id?: string
  agent_name?: string
  recoverable: boolean
}

/**
 * Event emitted for log messages during pipeline execution
 */
export interface PipelineLogEvent extends PipelineEvent {
  type: 'pipeline_log'
  level: LogLevel
  message: string
}

/**
 * Union type for all pipeline events
 */
export type AnyPipelineEvent =
  | PipelineStartEvent
  | AgentStartEvent
  | AgentCompleteEvent
  | TechCompleteEvent
  | PipelineProgressEvent
  | PipelineCompleteEvent
  | PipelineErrorEvent
  | PipelineLogEvent

/**
 * Pipeline execution status
 */
export interface PipelineStatus {
  is_running: boolean
  current_tech_count?: number
  progress_percent?: number
  started_at?: string
  estimated_completion?: string
}

/**
 * Agent status for UI display
 */
export interface AgentStatus {
  name: string
  display_name: string
  status: 'pending' | 'active' | 'completed' | 'error'
  start_time?: number
  end_time?: number
  error?: string
}

/**
 * Technology progress for UI display
 */
export interface TechnologyProgress {
  tech_id: string
  tech_name: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  phase?: string
  current_agent?: string
  error?: string
}

/**
 * Pipeline runner state
 */
export interface PipelineRunnerState {
  stage: 'config' | 'running' | 'completed' | 'error'
  config?: PipelineConfig
  progress: number // 0-100
  current_tech?: string
  current_agent?: string
  agents: AgentStatus[]
  technologies: TechnologyProgress[]
  logs: PipelineLogEvent[]
  error?: string
  duration_seconds?: number
  chart_data?: HypeCycleChartData
}

/**
 * Default pipeline configuration
 */
export const DEFAULT_PIPELINE_CONFIG: PipelineConfig = {
  tech_count: 50,
  community_version: 'v1',
  enable_tavily: true,
  min_docs: 5,
  verbosity: 'normal',
}

/**
 * Agent definitions for UI display
 */
export const AGENT_DEFINITIONS: Array<{
  name: string
  display_name: string
  description: string
}> = [
  {
    name: 'tech_discovery',
    display_name: 'Tech Discovery',
    description: 'Discover technologies from Neo4j communities',
  },
  {
    name: 'innovation_scorer',
    display_name: 'Innovation Scorer',
    description: 'Score based on patents, papers, GitHub activity',
  },
  {
    name: 'adoption_scorer',
    display_name: 'Adoption Scorer',
    description: 'Score based on contracts, regulations, job postings',
  },
  {
    name: 'narrative_scorer',
    display_name: 'Narrative Scorer',
    description: 'Score based on news sentiment and volume',
  },
  {
    name: 'risk_scorer',
    display_name: 'Risk Scorer',
    description: 'Score based on SEC filings, insider trading',
  },
  {
    name: 'hype_scorer',
    display_name: 'Hype Scorer',
    description: 'Calculate hype from layer divergence',
  },
  {
    name: 'phase_detector',
    display_name: 'Phase Detector',
    description: 'Determine hype cycle phase position',
  },
  {
    name: 'llm_analyst',
    display_name: 'LLM Analyst',
    description: 'Generate executive summary with GPT-4',
  },
  {
    name: 'ensemble',
    display_name: 'Ensemble',
    description: 'Calculate final X/Y positioning',
  },
  {
    name: 'chart_generator',
    display_name: 'Chart Generator',
    description: 'Format data for D3.js visualization',
  },
  {
    name: 'evidence_compiler',
    display_name: 'Evidence Compiler',
    description: 'Collect supporting documents and metrics',
  },
  {
    name: 'validator',
    display_name: 'Validator',
    description: 'Verify output structure and quality',
  },
]

/**
 * Get agent display name from agent name
 */
export function getAgentDisplayName(agentName: string): string {
  const agent = AGENT_DEFINITIONS.find((a) => a.name === agentName)
  return agent?.display_name || agentName
}

/**
 * Get initial agent status list
 */
export function getInitialAgentStatuses(): AgentStatus[] {
  return AGENT_DEFINITIONS.map((agent) => ({
    name: agent.name,
    display_name: agent.display_name,
    status: 'pending',
  }))
}
