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
│   │   └── useEvidenceData.ts               # Fetch evidence
│   │
│   ├── types/
│   │   └── hypeCycle.ts                     # TypeScript interfaces
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
npm install
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

### Production (Phase 4/5 Integration)

```
Phase 4/5 Multi-Agent System
  └── Outputs JSON files
       ↓
FastAPI Backend
  └── GET /api/hype-cycle/{industry}
  └── POST /api/neo4j/query
       ↓
React Frontend
  └── Fetch + Render
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

## Integration with Phase 4/5

When Phase 4/5 multi-agent system is ready:

1. **Replace mock data fetching**:
```typescript
// Before (mock)
const data = await fetch('/mock-data/hype_cycle_chart.json');

// After (production)
const data = await fetch('/api/hype-cycle/evtol');
```

2. **Add WebSocket for real-time agent progress**:
```typescript
const ws = new WebSocket('/ws/agents');
ws.onmessage = (event) => {
  const { agent, status } = JSON.parse(event.data);
  updateProgress(agent, status);
};
```

3. **Neo4j subgraph queries**:
```typescript
// POST /api/neo4j/query
await fetch('/api/neo4j/query', {
  method: 'POST',
  body: JSON.stringify({
    cypher: `MATCH (t:Technology {id: $techId})-[r]-(n) RETURN t, r, n`
  })
});
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
- All scores calculated on-demand by Phase 4/5 agents using graph as RAG
- Same graph input → Same chart output (reproducibility for evaluations)

### Phase Separation
- Phase 6 (UI) receives JSON files from Phase 4/5
- NO direct Neo4j access from frontend (backend proxy for security)
- Clean interface contracts defined in `src/types/hypeCycle.ts`

## License

MIT License - Part of Pura Vida Sloth strategic intelligence platform
