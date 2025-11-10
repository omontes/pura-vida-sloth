/**
 * vis-network Configuration
 *
 * Extracted from data/samples-phase/phase6/code/neo4j_gradio_VIS.py
 * Professional dark/light theme styling with force-directed physics
 */

import type { Options } from 'vis-network';

// Theme colors based on user's Gradio prototype
interface ThemeColors {
  nodeFontColor: string;
  edgeColor: string;
  edgeHighlight: string;
  edgeHover: string;
  edgeFontColor: string;
  edgeFontBg: string;
  shadowColor: string;
}

const DARK_THEME: ThemeColors = {
  nodeFontColor: '#ffffff',
  edgeColor: 'rgba(150, 166, 186, 0.5)',
  edgeHighlight: 'rgba(20, 184, 166, 0.8)',  // Teal-500 for dark mode visibility
  edgeHover: 'rgba(20, 184, 166, 0.6)',
  edgeFontColor: '#97a6ba',
  edgeFontBg: 'rgba(12, 17, 23, 0.85)',
  shadowColor: 'rgba(0,0,0,0.3)',
};

const LIGHT_THEME: ThemeColors = {
  nodeFontColor: '#1a1d23',
  edgeColor: 'rgba(100, 116, 139, 0.4)',
  edgeHighlight: 'rgba(15, 118, 110, 0.8)',  // Teal-700 brand color
  edgeHover: 'rgba(15, 118, 110, 0.6)',
  edgeFontColor: '#5a6370',
  edgeFontBg: 'rgba(255, 255, 255, 0.85)',
  shadowColor: 'rgba(0,0,0,0.15)',
};

/**
 * Get vis-network options with theme-aware styling
 *
 * @param isDarkMode - Whether dark mode is active
 * @returns vis-network options object
 */
export function getVisNetworkOptions(isDarkMode: boolean): Options {
  const theme = isDarkMode ? DARK_THEME : LIGHT_THEME;

  return {
    nodes: {
      shape: 'dot',
      borderWidth: 2,
      borderWidthSelected: 3,
      shadow: {
        enabled: true,
        color: theme.shadowColor,
        size: 8,
        x: 0,
        y: 2,
      },
      font: {
        color: theme.nodeFontColor,
        size: 13,
        face: 'Inter, sans-serif',
        bold: '600',
      },
    },
    edges: {
      width: 2,
      color: {
        color: theme.edgeColor,
        highlight: theme.edgeHighlight,
        hover: theme.edgeHover,
      },
      arrows: {
        to: {
          enabled: true,
          scaleFactor: 0.8,
        },
      },
      smooth: {
        enabled: true,
        type: 'dynamic',
        roundness: 0.5,
      },
      font: {
        size: 11,
        color: theme.edgeFontColor,
        background: theme.edgeFontBg,
        strokeWidth: 0,
        align: 'horizontal',
      },
    },
    physics: {
      enabled: true,
      stabilization: {
        enabled: true,
        iterations: 250,
        updateInterval: 25,
        fit: true,
      },
      barnesHut: {
        gravitationalConstant: -30000,
        centralGravity: 0.3,
        springLength: 180,
        springConstant: 0.04,
        damping: 0.5,
        avoidOverlap: 0.3,
      },
      minVelocity: 0.75,
      maxVelocity: 50,
    },
    interaction: {
      hover: true,
      navigationButtons: false,
      keyboard: true,
      tooltipDelay: 100,
      hideEdgesOnDrag: false,
      hideEdgesOnZoom: false,
    },
  };
}

/**
 * Node color palette (adapted for Canopy Intelligence entity types)
 *
 * Based on user's Gradio prototype PALETTE
 */
export const NODE_COLORS: Record<string, string> = {
  // Entity types (Primary hierarchy - high visual weight)
  Technology: '#0f766e',   // Teal (brand color) - PRIMARY NODE
  Company: '#f59e0b',      // Amber (warm contrast) - ACTION/ENTERPRISE
  Person: '#59a14f',       // Green (kept original)

  // Document types (Secondary hierarchy - subtle grays with slight variations)
  Patent: '#64748b',              // Slate-500 (blue-gray medium)
  TechnicalPaper: '#94a3b8',      // Slate-400 (blue-gray light)
  SECFiling: '#475569',           // Slate-600 (blue-gray dark)
  Regulation: '#71717a',          // Zinc-500 (neutral gray)
  GitHub: '#78716c',              // Stone-500 (warm gray)
  GovernmentContract: '#57534e',  // Stone-600 (warm gray dark)
  News: '#a8a29e',                // Stone-400 (warm gray light)
  InsiderTransaction: '#6b7280',  // Gray-500 (pure gray)
  StockPrice: '#9ca3af',          // Gray-400 (pure gray light)
  InstitutionalHolding: '#52525b', // Zinc-600 (neutral dark gray)
};

/**
 * Get color for a node type (with fallback)
 *
 * @param nodeType - Node label/type
 * @returns Hex color string
 */
export function getNodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType] || '#8892a6';
}

/**
 * Calculate node size based on degree (number of connections)
 *
 * @param degree - Number of connections
 * @returns Node size in pixels
 */
export function calculateNodeSize(degree: number): number {
  return 30 + degree * 3;
}

/**
 * Create HTML tooltip for a node
 *
 * @param nodeLabel - Node type/label
 * @param properties - Node properties
 * @returns HTML string for tooltip
 */
export function createNodeTooltip(
  nodeLabel: string,
  properties: Record<string, any>
): string {
  const lines: string[] = [`<b>${nodeLabel}</b>`];

  // Show top 5 properties
  const propEntries = Object.entries(properties)
    .filter(([key, value]) => {
      // Exclude embedding and search_corpus properties
      return (
        value !== null &&
        value !== undefined &&
        !key.toLowerCase().includes('embedding') &&
        !key.toLowerCase().includes('search_corpus')
      );
    })
    .slice(0, 5);

  propEntries.forEach(([key, value]) => {
    let displayValue = String(value);
    if (displayValue.length > 50) {
      displayValue = displayValue.substring(0, 47) + '...';
    }
    lines.push(`${key}: ${displayValue}`);
  });

  return lines.join('<br>');
}
