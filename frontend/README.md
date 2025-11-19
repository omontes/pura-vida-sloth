# Pura Vida Sloth - Phase 5 Frontend

**Executive-grade Hype Cycle visualization + Multi-Agentic Pipeline for strategic technology market research**

## Overview

React + TypeScript frontend featuring:
- **Multi-Agent Pipeline Execution** (WebSocket-based real-time streaming)
- **Gartner-style Hype Cycle chart** (D3.js custom curve)
- **Interactive Neo4j graph visualization** (vis.js force-directed layout)
- **Technology drill-down** with evidence cards grouped by intelligence layer
- **Run History Management** (save, view, switch between pipeline runs)
- **Professional C-level design** optimized for executive presentations

## Tech Stack

- **Framework**: React 18 + TypeScript + Vite
- **Visualization**: D3.js v7, vis-network-react
- **State Management**: React Query, Zustand
- **UI Components**: Radix UI (headless components)
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion

## Project Structure

```
frontend/
├── public/
│   └── mock-data/                    # Mock Phase 4/5 outputs
│       ├── hype_cycle_chart.json     # Main chart data (15 technologies)
│       ├── evidence_report.json      # Supporting documents
│       └── neo4j_subgraphs.json      # Graph visualization data
│
├── src/
│   ├── components/
│   │   ├── charts/
│   │   │   ├── HypeCycleChart.tsx           # Main D3 chart
│   │   │   ├── TechnologyNode.tsx           # Tech bubble on curve
│   │   │   └── PhaseLabels.tsx              # Phase separators
│   │   │
│   │   ├── graph/
│   │   │   └── Neo4jGraphViz.tsx            # vis-network graph
│   │   │
│   │   ├── pipeline/
│   │   │   ├── PipelineRunner.tsx           # Main pipeline modal
│   │   │   ├── RunHistory.tsx               # Run history dropdown
│   │   │   ├── LogViewer.tsx                # Console-style log viewer
│   │   │   ├── ProgressTracker.tsx          # Progress bar + agent checklist
│   │   │   └── ConfigForm.tsx               # Pipeline configuration form
│   │   │
│   │   ├── technology/
│   │   │   ├── TechnologyDetail.tsx         # Modal drill-down
│   │   │   ├── EvidenceSection.tsx          # Layer-grouped evidence
│   │   │   └── EvidenceCard.tsx             # Individual doc card
│   │   │
│   │   └── layout/
│   │       └── Header.tsx                   # Logo, industry selector
│   │
│   ├── config/
│   │   └── visNetworkConfig.ts              # vis.js physics + styling
│   │
│   ├── utils/
│   │   └── hypeCycleCurve.ts                # D3 curve generator
│   │
│   ├── hooks/
│   │   ├── useHypeCycleData.ts              # Fetch chart data
│   │   ├── useEvidenceData.ts               # Fetch evidence
│   │   ├── usePipelineWebSocket.ts          # WebSocket connection lifecycle
│   │   └── useRunHistory.ts                 # Run history management
│   │
│   ├── types/
│   │   ├── hypeCycle.ts                     # TypeScript interfaces
│   │   └── pipeline.ts                      # Pipeline event types
│   │
│   └── App.tsx                              # Main router
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install --legacy-peer-deps  # Use --legacy-peer-deps to avoid conflicts
```

### 2. Run Development Server

```bash
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173)

### 3. Build for Production

```bash
npm run build
npm run preview
```

## Pipeline Execution

### Overview

The frontend provides a complete interface for executing the multi-agent pipeline and managing run history.

### 4-Stage Workflow

#### 1. Configuration Stage
- Select technology count (1-200)
- Choose community version (v0, v1, v2)
- Enable/disable Tavily search
- Set minimum documents per source (1-20)
- View estimated duration

#### 2. Running Stage
- Real-time WebSocket streaming
- Progress bar (0-100%)
- Agent status tracking (12 agents with icons)
- Live log viewer with auto-scroll
- Technology counter (e.g., "5 / 50")
- Duration timer (MM:SS format)
- Current technology display

#### 3. Completed Stage
- Success message with summary
- Total techs and phases covered
- Full execution duration
- Collapsible log viewer
- "View Updated Chart" button
- Chart auto-updates via React Query

#### 4. Error Handling
- Error message displayed
- Full logs shown for debugging
- Graceful disconnect handling (pipeline continues server-side)
- Retry capability

### Running the Pipeline

```typescript
// Click "Run Multi-Agent" button in UI
// Configure settings:
// - Tech count: 50
// - Community version: v1 (recommended)
// - Enable Tavily: Yes (for enhanced web search)
// - Min docs: 5

// Pipeline executes 12 agents:
// 1. Tech Discovery → 2. Innovation Scorer → 3. Adoption Scorer
// 4. Narrative Scorer → 5. Risk Scorer → 6. Hype Scorer
// 7. Phase Detector → 8. LLM Analyst → 9. Ensemble
// 10. Chart Generator → 11. Evidence Compiler → 12. Validator

// Results automatically saved to:
// src/agents/run_history/{run_id}/
//   ├── hype_cycle_chart.json (normalized, top 5 per phase)
//   ├── hype_cycle_chart_full.json (all technologies)
//   └── metadata.json (config, duration, tech count)
```

## Key Features

### Hype Cycle Chart

**Technology**: D3.js with custom Bezier curve

**Key Requirements**:
- Technology nodes positioned **ON** the curve line (not floating)
- 5 phase separators (vertical dashed lines)
- Phase labels with color coding
- Hover effects (scale 1.2x)
- Click to drill-down to evidence

**Code Example**:
```tsx
import { HypeCycleChart } from '@/components/charts/HypeCycleChart';

<HypeCycleChart
  technologies={technologies}
  onTechnologyClick={(techId) => openDetailModal(techId)}
/>
```

### Neo4j Graph Visualization

**Technology**: vis-network-react (vis.js wrapper)

**Features**:
- Force-directed layout with Barnes-Hut algorithm
- Dark/light theme support
- Interactive physics simulation
- Node click → property details panel
- Controls: Reset View, Toggle Physics, Fullscreen

**Code Example**:
```tsx
import { Neo4jGraphViz } from '@/components/graph/Neo4jGraphViz';

<Neo4jGraphViz technologyId="evtol" />
```

**Configuration** (extracted from Gradio prototype):
```typescript
// src/config/visNetworkConfig.ts
export const getVisNetworkOptions = (isDarkMode: boolean) => ({
  physics: {
    barnesHut: {
      gravitationalConstant: -10000,
      centralGravity: 0.3,
      springLength: 180,
      springConstant: 0.04,
      damping: 0.5,
      avoidOverlap: 0.3
    }
  },
  nodes: {
    shape: 'dot',
    shadow: { enabled: true, size: 8 }
  }
});
```

### Pipeline Components

#### PipelineRunner
**Purpose**: Main modal component orchestrating the complete pipeline execution workflow.

**Key Features**:
- Four-stage workflow: Config → Running → Completed → Error
- Real-time progress tracking via WebSocket
- Live log streaming with auto-scroll
- Professional C-level UI with smooth animations
- Automatic chart updates on completion
- Handles disconnections gracefully (pipeline continues server-side)

**Code Example**:
```tsx
import { PipelineRunner } from '@/components/pipeline/PipelineRunner';

<PipelineRunner
  isOpen={showPipeline}
  onClose={() => setShowPipeline(false)}
  onComplete={(techCount) => {
    console.log(`Pipeline completed with ${techCount} technologies`);
    // Chart auto-updates via React Query
  }}
/>
```

#### RunHistory
**Purpose**: Dropdown selector for viewing and managing past pipeline runs.

**Key Features**:
- Lists runs newest-first with metadata
- Shows: timestamp (UTC-6), tech count, duration, community version
- Visual indicator for currently active run
- Delete functionality with confirmation
- Formatted timestamps (`Jan 10, 2:30 PM`)
- Formatted durations (`2m 15s`)

**Code Example**:
```tsx
import { RunHistory } from '@/components/pipeline/RunHistory';

<RunHistory
  onRunSelect={(runId) => {
    console.log(`Switched to run: ${runId}`);
    // Chart updates to show historical data
  }}
/>
```

#### LogViewer
**Purpose**: Console-style log viewer for pipeline execution.

**Key Features**:
- Color-coded by log level (debug/info/warning/error)
- Auto-scroll with lock/unlock toggle
- Export logs to `.txt` file
- Monospace font for readability
- UTC-6 timezone display for timestamps
- Scroll lock detection (disables auto-scroll when user scrolls up)

**Code Example**:
```tsx
import { LogViewer } from '@/components/pipeline/LogViewer';

<LogViewer
  logs={pipelineLogs}
  maxHeight={400}  // Optional, default 400px
/>
```

**Log Levels**:
- `debug`: Gray (for LLM calls, detailed traces)
- `info`: Blue (general progress)
- `warning`: Yellow (recoverable issues)
- `error`: Red (failures)

#### ProgressTracker
**Purpose**: Visual progress indicator with agent status checklist.

**Key Features**:
- Overall progress bar (0-100%)
- Current agent display with friendly names
- Technology counter (`5 / 50`)
- Live duration timer (MM:SS format)
- Agent checklist with status icons (○ pending, ⟳ active, ✓ completed, ✗ error)
- Per-agent duration display
- Current technology display with formatting

**Code Example**:
```tsx
import { ProgressTracker } from '@/components/pipeline/ProgressTracker';

<ProgressTracker
  progress={45}
  currentAgent="scorer_innovation"
  currentTech="evtol"
  techCount={5}
  totalTechs={50}
  agents={agentStatuses}
  startTime={Date.now()}
/>
```

#### ConfigForm
**Purpose**: Configuration form for pipeline execution.

**Key Features**:
- Technology count slider (10-100) + numeric input (1-200)
- Community version selector (v0/v1/v2) with radio buttons
- Tavily search toggle with description
- Minimum documents input (1-20)
- Validation with error messages
- Estimated duration display (`~5m`)
- Helpful tip text at bottom

**Code Example**:
```tsx
import { ConfigForm } from '@/components/pipeline/ConfigForm';

<ConfigForm
  onSubmit={(config) => {
    console.log('Starting pipeline with config:', config);
    // Config includes: tech_count, community_version, enable_tavily, min_docs
  }}
  onCancel={() => console.log('User cancelled')}
  disabled={isRunning}
/>
```

## Data Flow

### Mock Data (Development)

```
Public Directory
  └── mock-data/*.json
       ↓
React Components (fetch on mount)
       ↓
State Management (React Query)
       ↓
Visualization Rendering
```

### Production (Phase 5 Integration)

```
User Initiates Pipeline
       ↓
PipelineRunner Component
  └── usePipelineWebSocket hook
       ↓
WebSocket Connection (ws://localhost/api/pipeline/ws/run)
       ↓
FastAPI Backend (pipeline_service.py)
  └── Executes 12-agent LangGraph workflow
  └── Streams real-time events
       ↓
Frontend receives events:
  - pipeline_start
  - agent_start / agent_complete (x12)
  - tech_complete (x tech_count)
  - pipeline_log
  - pipeline_complete (with chart data)
       ↓
RunHistoryService saves:
  └── src/agents/run_history/{run_id}/
      ├── hype_cycle_chart.json
      ├── hype_cycle_chart_full.json
      └── metadata.json
       ↓
React Query invalidates cache
       ↓
Chart auto-updates with new data
```

## Mock Data Format

### `hype_cycle_chart.json`

```json
{
  "industry": "eVTOL",
  "technologies": [
    {
      "id": "evtol",
      "name": "eVTOL",
      "phase": "Peak of Inflated Expectations",
      "phase_confidence": 0.88,
      "chart_x": 1.75,           // X position on curve (0-5 scale)
      "scores": {
        "innovation": 72.5,       // Layer 1 (Patents, Papers, GitHub)
        "adoption": 35.8,          // Layer 2 (Gov Contracts, Regulations)
        "narrative": 84.2,         // Layer 4 (News, PR)
        "risk": 58.3,              // Layer 3 (SEC, Insider Trading)
        "hype": 68.7               // Combined hype score
      },
      "summary": "High media coverage but minimal revenue...",
      "evidence_counts": {
        "patents": 42,
        "news": 269
      }
    }
  ]
}
```

## Pipeline Hooks

### usePipelineWebSocket

**Purpose**: Custom hook managing WebSocket connection lifecycle and event streaming.

**Return Interface**:
```typescript
interface UsePipelineWebSocketReturn {
  state: PipelineRunnerState
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'error'
  connect: (config: PipelineConfig) => void
  disconnect: () => void
  reset: () => void
  error: string | null
}
```

**Key Functions**:

1. **connect(config)**: Establishes WebSocket connection and sends config
   - URL: `ws://localhost:PORT/api/pipeline/ws/run` (auto-detects wss for HTTPS)
   - Immediate UI feedback (transitions to "running" before server response)
   - Sends config JSON on connection open

2. **handleEvent(event)**: Processes incoming WebSocket events
   - `pipeline_start`: Initialize agents, clear logs
   - `agent_start`: Update current agent, mark as active
   - `agent_complete`: Mark agent as completed with end time
   - `tech_complete`: Update technology progress, recalculate percentage
   - `pipeline_progress`: General progress updates
   - `pipeline_complete`: Set stage to completed, store chart data
   - `pipeline_error`: Set error stage
   - `pipeline_log`: Append to log array

3. **disconnect()**: Gracefully close connection (code 1000)

4. **reset()**: Reset to initial config stage (called when modal reopens)

**Usage Example**:
```typescript
import { usePipelineWebSocket } from '@/hooks/usePipelineWebSocket';

function CustomPipelineUI() {
  const { state, connectionState, connect, disconnect, reset } = usePipelineWebSocket();

  const handleStart = () => {
    connect({
      tech_count: 50,
      community_version: 'v1',
      enable_tavily: true,
      min_docs: 5,
      verbosity: 'normal'
    });
  };

  return (
    <div>
      <button onClick={handleStart}>Start Pipeline</button>
      <div>Stage: {state.stage}</div>
      <div>Progress: {state.progress}%</div>
      <div>Logs: {state.logs.length}</div>
    </div>
  );
}
```

### useRunHistory

**Purpose**: Hook for managing pipeline run history with React Query caching.

**Return Interface**:
```typescript
{
  // Run list
  runs: RunMetadata[]
  runCount: number
  isLoadingRuns: boolean
  runsError: Error | null

  // Selected run
  selectedRunId: string | null
  selectedRun: RunData | null
  isLoadingRun: boolean
  runError: Error | null

  // Actions
  selectRun: (runId: string) => void
  deleteRun: (runId: string) => void
  isDeleting: boolean
  refreshRuns: () => void
}
```

**Key Features**:
- Uses React Query for automatic caching and invalidation
- Fetches run list on mount (`queryKey: ['pipelineRuns']`)
- Fetches specific run when selected (`queryKey: ['pipelineRun', runId]`)
- Delete mutation automatically refreshes list
- Clears selection if deleted run was active

**Usage Example**:
```typescript
import { useRunHistory } from '@/hooks/useRunHistory';

function RunSelector() {
  const { runs, selectRun, deleteRun, isDeleting } = useRunHistory();

  return (
    <div>
      {runs.map(run => (
        <div key={run.run_id}>
          <button onClick={() => selectRun(run.run_id)}>
            {run.created_at} - {run.tech_count} techs
          </button>
          <button
            onClick={() => deleteRun(run.run_id)}
            disabled={isDeleting}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}
```

## Pipeline API Endpoints

### WebSocket Endpoint

**URL**: `ws://localhost:PORT/api/pipeline/ws/run`

**Protocol**:
1. Client connects
2. Client sends `PipelineConfig` as JSON
3. Server validates config
4. Server streams events (`pipeline_start`, `agent_start`, etc.)
5. Server sends `pipeline_complete` with full chart
6. Connection closes

**Config Schema**:
```json
{
  "tech_count": 50,
  "community_version": "v1",
  "enable_tavily": true,
  "min_docs": 5,
  "verbosity": "normal"
}
```

**Event Types**:
- `pipeline_start`: Pipeline begins
- `agent_start`: Agent starts processing tech
- `agent_complete`: Agent finishes
- `tech_complete`: Technology completes all agents
- `pipeline_progress`: General progress update
- `pipeline_log`: Log message (info/debug/warning/error)
- `pipeline_complete`: Pipeline finishes successfully
- `pipeline_error`: Error occurred

**Example Event**:
```json
{
  "type": "tech_complete",
  "timestamp": "2025-01-10T20:30:45.123Z",
  "tech_id": "evtol",
  "tech_name": "eVTOL",
  "progress": 5,
  "total": 50,
  "phase": "Peak of Inflated Expectations"
}
```

### REST Endpoints

#### GET /api/pipeline/runs
List all pipeline runs (newest first).

**Query Params**:
- `limit` (optional): Max runs to return (default: 20)

**Response**:
```json
{
  "runs": [
    {
      "run_id": "2025-01-10_14-30-45_50tech_v1",
      "created_at": "2025-01-10T20:30:45.123Z",
      "config": { "tech_count": 50, "community_version": "v1", ... },
      "duration_seconds": 135.5,
      "tech_count": 50,
      "phases": ["Innovation Trigger", "Peak of Inflated Expectations", ...]
    }
  ],
  "count": 1
}
```

#### GET /api/pipeline/runs/{run_id}
Get complete data for specific run.

**Response**:
```json
{
  "run_id": "2025-01-10_14-30-45_50tech_v1",
  "chart_data": { "technologies": [...] },     // Normalized chart (top 5 per phase)
  "metadata": { "config": {...}, "duration_seconds": 135.5, ... },
  "original_chart": { "technologies": [...] }  // Full chart (all techs)
}
```

**Error**: `404 Not Found` if run doesn't exist

#### DELETE /api/pipeline/runs/{run_id}
Delete a pipeline run and all files.

**Response**:
```json
{
  "message": "Run '2025-01-10_14-30-45_50tech_v1' deleted successfully"
}
```

**Errors**:
- `404 Not Found`: Run doesn't exist
- `500 Internal Server Error`: Delete failed

#### GET /api/pipeline/status
Get current pipeline execution status.

**Response**:
```json
{
  "is_running": true,
  "current_tech_count": 50,
  "started_at": "2025-01-10T20:30:45.123Z"
}
```

## Run History Storage

**Directory Structure**:
```
src/agents/run_history/
  ├── 2025-01-10_14-30-45_50tech_v1/
  │   ├── hype_cycle_chart.json           # Normalized (top 5/phase)
  │   ├── hype_cycle_chart_full.json      # Original (all techs)
  │   └── metadata.json                   # Run metadata
  └── 2025-01-10_15-45-30_20tech_v2/
      └── ...
```

**Run ID Format**: `YYYY-MM-DD_HH-MM-SS_{count}tech_{version}`

Example: `2025-01-10_14-30-45_50tech_v1`

**Metadata Schema**:
```json
{
  "run_id": "2025-01-10_14-30-45_50tech_v1",
  "created_at": "2025-01-10T20:30:45.123Z",
  "config": {
    "tech_count": 50,
    "community_version": "v1",
    "enable_tavily": true,
    "min_docs": 5,
    "verbosity": "normal"
  },
  "duration_seconds": 135.5,
  "tech_count": 50,
  "phases": ["Innovation Trigger", "Peak of Inflated Expectations", ...]
}
```

**Features**:
- Each run saved to unique timestamped directory
- Normalized chart (top 5 techs per phase) for display
- Full chart preserved for analysis
- Metadata includes config, duration, tech count, phases
- Frontend fetches via `/api/pipeline/runs`
- Users can switch between runs to view historical charts
- Delete functionality removes entire run directory

## Development Guidelines

### Adding a New Technology

1. Add entry to `mock-data/hype_cycle_chart.json`
2. Set `chart_x` (0-5) based on phase:
   - Innovation Trigger: 0-1
   - Peak: 1-2
   - Trough: 2-3
   - Slope: 3-4
   - Plateau: 4-5
3. Node will auto-position ON curve via `getYForX()`

### Customizing Chart Appearance

**Curve Style**:
```typescript
// src/utils/hypeCycleCurve.ts
const line = d3.line<HypeCyclePoint>()
  .curve(d3.curveCatmullRom.alpha(0.5))  // Adjust alpha (0-1)
```

**Phase Colors**:
```typescript
export const PHASE_COLORS = {
  'Innovation Trigger': '#3b82f6',         // Blue
  'Peak of Inflated Expectations': '#ef4444', // Red
  // ...customize as needed
};
```

**Node Size**:
```typescript
// Radius = base + evidence count scaling
.attr('r', d => 8 + (Object.values(d.evidence_counts).reduce((a, b) => a + b, 0) / 30))
```

### Customizing Neo4j Graph

**Node Colors**:
```typescript
// src/config/visNetworkConfig.ts
export const NODE_COLORS = {
  Technology: '#4e79a7',
  Company: '#f28e2b',
  Patent: '#e15759',
  // ...add more as needed
};
```

**Physics Settings**:
```typescript
// Adjust force-directed layout
physics: {
  barnesHut: {
    gravitationalConstant: -10000,  // Repulsion force
    springLength: 180,              // Edge length
    damping: 0.5                    // Movement damping
  }
}
```

## Performance Optimization

### Chart Rendering
- D3 uses SVG (fast for <100 nodes)
- React useEffect dependency: only re-render when `technologies` changes
- Hover effects use CSS transforms (GPU-accelerated)

### Graph Rendering
- vis.js auto-pauses physics after stabilization
- Large graphs (>500 nodes): Use `hierarchical` layout instead of Barnes-Hut
- Filter out `embedding` properties to reduce data transfer

## Deployment

### Environment Variables

```bash
# .env.production
VITE_API_BASE_URL=https://api.puravidasloth.com
VITE_NEO4J_ENABLED=true
```

### Build Configuration

```typescript
// vite.config.ts
export default defineConfig({
  base: '/app/',  // If deploying to subdirectory
  build: {
    outDir: 'dist',
    sourcemap: true
  }
});
```

## Integration with Phase 5 Multi-Agent System

The frontend is fully integrated with the FastAPI backend for real-time pipeline execution.

### Backend Architecture

**FastAPI Backend** (`src/api/`):
- `pipeline_routes.py`: WebSocket and REST endpoints
- `pipeline_service.py`: Executes LangGraph orchestrator, streams events
- `run_history_service.py`: Manages run persistence and retrieval
- `pipeline_schemas.py`: Pydantic validation for events and config

**Multi-Agent System** (`src/agents/`):
- `langgraph_orchestrator.py`: 12-agent LangGraph state machine
- Agents: Tech Discovery, 5 Scorers, Phase Detector, LLM Analyst, Ensemble, Chart Generator, Evidence Compiler, Validator

### Real-Time Communication Flow

```typescript
// 1. User clicks "Run Multi-Agent" button
<PipelineRunner isOpen={true} onClose={...} onComplete={...} />

// 2. PipelineRunner uses usePipelineWebSocket hook
const { connect } = usePipelineWebSocket()
connect({
  tech_count: 50,
  community_version: 'v1',
  enable_tavily: true,
  min_docs: 5,
  verbosity: 'normal'
})

// 3. WebSocket connects to FastAPI
// ws://localhost:8000/api/pipeline/ws/run

// 4. Backend executes LangGraph workflow
// - Discovers technologies from Neo4j communities
// - Runs 12 agents sequentially for each tech
// - Streams events to frontend in real-time

// 5. Frontend receives and processes events
// - pipeline_start: Initialize UI
// - agent_start: Update current agent (12x)
// - tech_complete: Update progress (tech_count times)
// - pipeline_log: Append to log viewer
// - pipeline_complete: Show results, save run

// 6. RunHistoryService saves complete run
// src/agents/run_history/{run_id}/
//   ├── hype_cycle_chart.json
//   ├── hype_cycle_chart_full.json
//   └── metadata.json

// 7. React Query invalidates cache
queryClient.invalidateQueries({ queryKey: ['hypeCycleData'] })

// 8. Chart auto-updates with new data
```

### Complete Integration Example

```typescript
import { useState } from 'react'
import { PipelineRunner } from '@/components/pipeline/PipelineRunner'
import { RunHistory } from '@/components/pipeline/RunHistory'
import { useRunHistory } from '@/hooks/useRunHistory'
import { HypeCycleChart } from '@/components/charts/HypeCycleChart'
import { useQuery, useQueryClient } from '@tanstack/react-query'

function App() {
  const [showPipeline, setShowPipeline] = useState(false)
  const { selectedRunId, selectedRun, selectRun, refreshRuns } = useRunHistory()
  const queryClient = useQueryClient()

  // Fetch chart data (latest or selected run)
  const { data: chartData } = useQuery({
    queryKey: ['hypeCycleData', selectedRunId],
    queryFn: async () => {
      if (selectedRunId && selectedRun) {
        return selectedRun.chart_data
      }
      // Fetch latest from frontend/public/data/hype_cycle_chart.json
      const response = await fetch('/data/hype_cycle_chart.json')
      return response.json()
    }
  })

  const handlePipelineComplete = (techCount?: number) => {
    console.log(`Pipeline completed with ${techCount} technologies`)
    selectRun(null)  // Clear selection to show latest
    refreshRuns()    // Refresh run history dropdown
    // Chart auto-updates via React Query invalidation
  }

  return (
    <div>
      {/* Header with run controls */}
      <Header>
        <button onClick={() => setShowPipeline(true)}>
          Run Multi-Agent Pipeline
        </button>
        <RunHistory onRunSelect={selectRun} />
      </Header>

      {/* Main chart */}
      <HypeCycleChart
        technologies={chartData?.technologies || []}
        onTechnologyClick={(techId) => console.log(techId)}
      />

      {/* Pipeline runner modal */}
      <PipelineRunner
        isOpen={showPipeline}
        onClose={() => setShowPipeline(false)}
        onComplete={handlePipelineComplete}
      />
    </div>
  )
}
```

### Backend Configuration

**Start FastAPI Server**:
```bash
cd backend
uvicorn src.api.main:app --reload --port 8000
```

**WebSocket URL**: Auto-detected by frontend
- Development: `ws://localhost:8000/api/pipeline/ws/run`
- Production: `wss://api.puravidasloth.com/api/pipeline/ws/run`

**Neo4j Configuration** (`.env`):
```bash
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

## Troubleshooting

### Issue: Nodes not positioned on curve

**Solution**: Ensure `getYForX()` is called, not `yScale(d.chart_y)`:
```typescript
// ❌ Wrong
const y = yScale(d.chart_y);

// ✅ Correct
const y = getYForX(d.chart_x);
```

### Issue: vis.js graph not rendering

**Solution**: Check container has explicit height:
```tsx
<div className="h-[600px]">  {/* Must have height */}
  <Graph graph={data} options={options} />
</div>
```

### Issue: TypeScript errors with vis-network

**Solution**: Install type definitions:
```bash
npm install --save-dev @types/vis-network
```

### Issue: WebSocket connection fails

**Solution**: Ensure FastAPI backend is running:
```bash
cd backend
uvicorn src.api.main:app --reload --port 8000
```

Check browser console for connection errors. WebSocket URL auto-detects from `window.location`.

### Issue: Pipeline modal shows old completion state

**Solution**: This should be automatically handled by the `reset()` function in `usePipelineWebSocket`. If persisting, clear React state:
```typescript
// The reset() function is called automatically when modal opens
useEffect(() => {
  if (isOpen) {
    reset()
  }
}, [isOpen, reset])
```

### Issue: Chart not updating after pipeline completion

**Solution**: Ensure React Query cache is being invalidated:
```typescript
import { useQueryClient } from '@tanstack/react-query'

const queryClient = useQueryClient()

const handlePipelineComplete = () => {
  queryClient.invalidateQueries({ queryKey: ['hypeCycleData'] })
}
```

### Issue: Run history not loading

**Solution**: Check that run history files exist:
```bash
ls src/agents/run_history/
# Should show directories like: 2025-01-10_14-30-45_50tech_v1/
```

Verify FastAPI endpoint is accessible:
```bash
curl http://localhost:8000/api/pipeline/runs
```

### Issue: Logs not showing in LogViewer

**Solution**: Ensure backend is emitting `pipeline_log` events:
```python
# In pipeline_service.py
logger = StreamingLogger(event_callback)
logger.info("Starting pipeline...")  # Will emit pipeline_log event
```

### Issue: Agent status icons not updating

**Solution**: Check that `agent_start` and `agent_complete` events include correct `agent_name`:
```json
{
  "type": "agent_start",
  "agent_name": "scorer_innovation",
  "tech_id": "evtol"
}
```

Agent names must match keys in `getInitialAgentStatuses()` in `usePipelineWebSocket.ts`.

## The 4-Layer Intelligence Framework

Understanding the data sources behind each score:

### Layer 1: Innovation Signals (Leading 18-24 months)
- **Sources**: Patents, Research Papers, GitHub Activity
- **Score**: `innovation` (0-100)
- **Purpose**: Predict technology emergence before commercialization

### Layer 2: Market Formation (Leading 12-18 months)
- **Sources**: Government Contracts, Regulatory Filings, Job Postings
- **Score**: `adoption` (0-100)
- **Purpose**: Predict when commercialization begins

### Layer 3: Financial Reality (Coincident 0-6 months)
- **Sources**: SEC Filings, Earnings, Stock Prices, Insider Trading
- **Score**: `risk` (0-100)
- **Purpose**: Measure current valuation vs actual performance

### Layer 4: Narrative (Lagging indicator)
- **Sources**: News Sentiment, Press Releases
- **Score**: `narrative` (0-100)
- **Purpose**: Detect media saturation peaks (contrarian indicator)

### Cross-Layer Contradiction Analysis

**The Magic**: When layers disagree, that reveals lifecycle position.

**Example - Peak Phase Indicators**:
- L1-2: Innovation slowing (GitHub inactive, patent decline)
- L3: Insiders selling, valuations stretched
- L4: Media coverage maximum
→ **Signal**: Market saturation risk

## Resources

- [D3.js Documentation](https://d3js.org/)
- [vis-network Documentation](https://visjs.github.io/vis-network/docs/network/)
- [Gartner Hype Cycle Methodology](https://www.gartner.com/en/research/methodologies/gartner-hype-cycle)
- [Radix UI Components](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)

## Architecture Principles

### Pure GraphRAG
- Neo4j contains ZERO derived scores (only raw data + relationships)
- All scores calculated on-demand by Phase 5 agents using graph as RAG
- Same graph input → Same chart output (reproducibility for evaluations)

### Phase Separation
- Phase 5 UI receives chart data from multi-agent pipeline
- NO direct Neo4j access from frontend (backend proxy for security)
- Clean interface contracts defined in `src/types/hypeCycle.ts` and `src/types/pipeline.ts`

### Real-Time Communication
- WebSocket-based streaming for immediate feedback
- FastAPI backend orchestrates LangGraph multi-agent system
- Frontend displays progress, logs, and agent status in real-time
- Run history preserved for comparison and analysis

## License

MIT License - Part of Pura Vida Sloth strategic intelligence platform
