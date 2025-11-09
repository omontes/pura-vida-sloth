/**
 * TypeScript interfaces for Canopy Intelligence Phase 6 UI
 * Defines the data contract between Phase 4/5 (Multi-Agent System) and Phase 6 (UI)
 */

export type LifecyclePhase =
  | 'Innovation Trigger'
  | 'Peak of Inflated Expectations'
  | 'Trough of Disillusionment'
  | 'Slope of Enlightenment'
  | 'Plateau of Productivity';

export type PhasePosition = 'early' | 'mid' | 'late';

export interface TechnologyScores {
  innovation: number;  // 0-100: Layer 1 (Patents, Papers, GitHub)
  adoption: number;    // 0-100: Layer 2 (Gov Contracts, Regulations)
  narrative: number;   // 0-100: Layer 4 (News, PR)
  risk: number;        // 0-100: Layer 3 (SEC, Insider Trading)
  hype: number;        // 0-100: Combined hype score
}

export interface EvidenceCounts {
  patents?: number;
  papers?: number;
  github?: number;
  news?: number;
  sec_filings?: number;
  insider_transactions?: number;
  government_contracts?: number;
  regulations?: number;
  [key: string]: number | undefined;
}

export interface Technology {
  id: string;
  name: string;
  domain: string;

  // Lifecycle Phase (from Ensemble Agent)
  phase: LifecyclePhase;
  phase_position?: PhasePosition;
  phase_confidence: number;  // 0-1

  // Chart Position (calculated by Chart Generator Agent)
  chart_x: number;  // 0-5 scale (phase index + offset)
  chart_y: number;  // 0-1 scale (normalized narrative_score)

  // Scores
  scores: TechnologyScores;

  // Summary & Analysis
  summary: string;
  key_contradictions?: string[];

  // Evidence
  evidence_counts: EvidenceCounts;

  // Related Entities
  companies_developing: string[];
  companies_using: string[];
}

export interface HypeCycleChartData {
  industry: string;
  generated_at: string;  // ISO 8601 timestamp
  metadata: {
    total_documents: number;
    date_range: string;
  };
  technologies: Technology[];
}

// Evidence Types

export type EvidenceType =
  | 'patent'
  | 'paper'
  | 'github'
  | 'news'
  | 'sec_filing'
  | 'insider_transaction'
  | 'government_contract'
  | 'regulation'
  | 'stock_price'
  | 'institutional_holding';

export type EvidenceLayer = 'innovation' | 'adoption' | 'narrative' | 'risk';

export interface Evidence {
  id: string;
  type: EvidenceType;
  title: string;
  date: string;  // ISO 8601 date
  source: string;
  strength: number;  // 0-1
  summary: string;
  url?: string;
}

export interface TechnologyEvidence {
  innovation_evidence: Evidence[];
  adoption_evidence: Evidence[];
  narrative_evidence: Evidence[];
  risk_evidence: Evidence[];
}

export interface EvidenceReport {
  technologies: {
    [techId: string]: TechnologyEvidence;
  };
}

// Neo4j Graph Types

export type NodeType =
  | 'Technology'
  | 'Company'
  | 'Person'
  | 'Patent'
  | 'TechnicalPaper'
  | 'SECFiling'
  | 'Regulation'
  | 'GitHub'
  | 'GovernmentContract'
  | 'News'
  | 'InsiderTransaction'
  | 'StockPrice'
  | 'InstitutionalHolding';

export interface GraphNode {
  id: string;
  label: NodeType;
  properties: Record<string, any>;
  degree?: number;  // Number of connections
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export interface Neo4jSubgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Neo4jSubgraphData {
  technologies: {
    [techId: string]: Neo4jSubgraph;
  };
}

// vis.js Graph Types (for vis-network-react)

export interface VisNode {
  id: string;
  label: string;
  color: string;
  size: number;
  font: {
    size: number;
    face: string;
    bold: string;
    color?: string;
  };
  group: string;
  title: string;  // HTML tooltip
  properties: Record<string, any>;
}

export interface VisEdge {
  from: string;
  to: string;
  label: string;
  arrows: string | { to: boolean };
  color: {
    color: string;
    highlight: string;
    hover?: string;
  };
  width: number;
  font?: {
    size: number;
    color: string;
    background: string;
    strokeWidth: number;
    align?: string;
  };
  properties?: Record<string, any>;
}

export interface VisGraphData {
  nodes: VisNode[];
  edges: VisEdge[];
}
