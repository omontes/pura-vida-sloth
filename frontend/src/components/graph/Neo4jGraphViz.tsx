/**
 * Neo4j Graph Visualization Component
 *
 * Uses vis-network-react to display Neo4j subgraphs with professional styling.
 * Configuration extracted from data/samples-phase/phase6/code/neo4j_gradio_VIS.py
 *
 * Features:
 * - Force-directed layout with Barnes-Hut physics
 * - Dark/light theme support
 * - Interactive controls (Reset View, Toggle Physics)
 * - Node type legend
 * - Property details panel on click
 */

import { useEffect, useState, useRef } from 'react';
import Graph from 'vis-network-react';
import {
  getVisNetworkOptions,
  getNodeColor,
  calculateNodeSize,
  createNodeTooltip,
} from '@/config/visNetworkConfig';
import type { Neo4jSubgraph, VisGraphData, VisNode, VisEdge } from '@/types/hypeCycle';
import { useTheme } from '@/contexts/ThemeContext';

interface Neo4jGraphVizProps {
  technologyId: string | null;
}

export default function Neo4jGraphViz({ technologyId }: Neo4jGraphVizProps) {
  const [graphData, setGraphData] = useState<VisGraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<VisNode | null>(null);
  const [physicsEnabled, setPhysicsEnabled] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const networkRef = useRef<any>(null);

  // Use theme context for dark/light mode
  const { themeMode } = useTheme();
  const isDarkMode = themeMode === 'dark';

  useEffect(() => {
    setIsLoading(true);
    setError(null);

    // Fetch subgraph from real Neo4j API
    // If technologyId is null, fetches full graph with all technologies
    // If technologyId is provided, fetches filtered subgraph for that technology
    fetch('/api/neo4j/subgraph', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tech_id: technologyId }),
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then((visData: VisGraphData) => {
        // Truncate node labels if longer than 23 characters
        const truncatedData = {
          ...visData,
          nodes: visData.nodes.map(node => ({
            ...node,
            label: node.label.length > 23
              ? node.label.substring(0, 20) + '...'
              : node.label
          }))
        };
        setGraphData(truncatedData);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Error loading Neo4j subgraph:', err);
        setError(err.message || 'Failed to load graph');
        setIsLoading(false);
      });
  }, [technologyId]);

  // Click events disabled to prevent navigation issues
  const events = {};

  const handleResetView = () => {
    if (networkRef.current) {
      networkRef.current.fit({
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad',
        },
      });
    }
  };

  const handleTogglePhysics = () => {
    if (networkRef.current) {
      const newState = !physicsEnabled;
      networkRef.current.setOptions({ physics: newState });
      setPhysicsEnabled(newState);
    }
  };

  // Always use normal force-directed physics layout
  const options = getVisNetworkOptions(isDarkMode, false);

  // Get unique node types for legend with hierarchical grouping
  const allNodeTypes = Array.from(
    new Set(graphData.nodes.map((n) => n.group))
  );

  // Define document types for grouping
  const documentTypes = [
    'Patent', 'TechnicalPaper', 'SECFiling', 'Regulation', 'GitHub',
    'GovernmentContract', 'News', 'InsiderTransaction', 'StockPrice', 'InstitutionalHolding'
  ];

  // Separate into categories with custom order
  const primaryNodes = allNodeTypes.filter(t => t === 'Technology');
  const companyNodes = allNodeTypes.filter(t => t === 'Company');
  const personNodes = allNodeTypes.filter(t => t === 'Person');
  const documentNodes = allNodeTypes.filter(t => documentTypes.includes(t)).sort();

  return (
    <div className="relative w-full h-[600px] bg-white dark:bg-gray-900 rounded-lg border border-gray-300 dark:border-gray-700">
      {/* vis-network graph */}
      {graphData.nodes.length > 0 && (
        <Graph
          data={graphData}
          options={options}
          events={events}
          getNetwork={(network) => {
            networkRef.current = network;

            // Auto-stop physics after stabilization to reduce CPU usage
            network.once('stabilizationIterationsDone', () => {
              setTimeout(() => {
                network.setOptions({ physics: false });
                setPhysicsEnabled(false);
              }, 30000); // 30 seconds for better layout quality
            });
          }}
        />
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              {technologyId ? 'Loading technology subgraph...' : 'Loading full knowledge graph...'}
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center max-w-md px-8">
            <div className="text-red-500 text-5xl mb-4">⚠️</div>
            <p className="text-gray-700 dark:text-gray-300 font-semibold mb-2">Failed to load graph</p>
            <p className="text-gray-600 dark:text-gray-500 text-sm">{error}</p>
            <p className="text-gray-500 dark:text-gray-600 text-xs mt-4">
              Make sure the FastAPI backend is running on port 8000
            </p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && graphData.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-600 dark:text-gray-400 text-sm">No graph data available</p>
          </div>
        </div>
      )}

      {/* Stats badge (top-left) */}
      <div className="absolute top-4 left-4 bg-white/95 dark:bg-gray-800/95 backdrop-blur border border-gray-300 dark:border-gray-700 rounded-lg px-4 py-2 text-xs text-gray-600 dark:text-gray-400">
        Nodes: <span className="font-bold text-teal-700 dark:text-teal-400">{graphData.nodes.length}</span> |
        Relationships: <span className="font-bold text-teal-700 dark:text-teal-400">{graphData.edges.length}</span>
      </div>

      {/* Legend (top-right) - Hierarchical */}
      {allNodeTypes.length > 0 && (
        <div className="absolute top-4 right-4 bg-white/95 dark:bg-gray-800/95 backdrop-blur border border-gray-300 dark:border-gray-700 rounded-lg p-4 max-w-xs max-h-96 overflow-y-auto">
          <div className="text-base font-bold text-teal-700 dark:text-teal-400 mb-3">Node Types</div>

          {/* Technology (Primary nodes) */}
          {primaryNodes.map((type) => (
            <div key={type} className="flex items-center gap-2 mb-2">
              <div
                className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-white/10"
                style={{ background: getNodeColor(type) }}
              />
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{type}</span>
            </div>
          ))}

          {/* Company nodes */}
          {companyNodes.map((type) => (
            <div key={type} className="flex items-center gap-2 mb-2 mt-3">
              <div
                className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-white/10"
                style={{ background: getNodeColor(type) }}
              />
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{type}</span>
            </div>
          ))}

          {/* Documents (Grouped category) */}
          {documentNodes.length > 0 && (
            <div className="mt-3 mb-2">
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">Document:</div>
              {documentNodes.map((type) => (
                <div key={type} className="flex items-center gap-2 mb-1.5 ml-3">
                  <div
                    className="w-3 h-3 rounded-full border border-gray-300 dark:border-white/10"
                    style={{ background: getNodeColor(type) }}
                  />
                  <span className="text-xs text-gray-600 dark:text-gray-400">{type}</span>
                </div>
              ))}
            </div>
          )}

          {/* Person nodes (if present) */}
          {personNodes.map((type) => (
            <div key={type} className="flex items-center gap-2 mb-2 mt-3">
              <div
                className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-white/10"
                style={{ background: getNodeColor(type) }}
              />
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{type}</span>
            </div>
          ))}
        </div>
      )}

      {/* Controls (bottom-left) */}
      <div className="absolute bottom-4 left-4 flex gap-2">
        <button
          onClick={handleResetView}
          className="px-4 py-2 bg-white/95 dark:bg-gray-800/95 backdrop-blur text-gray-700 dark:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition text-sm font-semibold border border-gray-300 dark:border-gray-700"
        >
          🔄 Reset View
        </button>
        <button
          onClick={handleTogglePhysics}
          className="px-4 py-2 bg-white/95 dark:bg-gray-800/95 backdrop-blur text-gray-700 dark:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition text-sm font-semibold border border-gray-300 dark:border-gray-700"
        >
          {physicsEnabled ? '⏸ Pause Physics' : '▶ Play Physics'}
        </button>
      </div>

      {/* Node info panel (bottom-left, appears on click) */}
      {selectedNode && (
        <div className="absolute bottom-20 left-4 bg-white/95 dark:bg-gray-800/95 backdrop-blur border border-gray-300 dark:border-gray-700 rounded-lg p-4 max-w-md max-h-96 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="text-base font-bold text-blue-600 dark:text-blue-400">
              {selectedNode.group}: {selectedNode.label}
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
            >
              ✕
            </button>
          </div>
          <table className="w-full text-xs">
            <tbody>
              {Object.entries(selectedNode.properties)
                .filter(([key]) => {
                  // Exclude embedding properties
                  return (
                    !key.toLowerCase().includes('embedding') &&
                    !key.toLowerCase().includes('search_corpus')
                  );
                })
                .map(([key, value]) => (
                  <tr key={key} className="border-b border-gray-300 dark:border-gray-700 last:border-0">
                    <th className="text-left pr-4 py-2 text-gray-600 dark:text-gray-400 font-medium">
                      {key}
                    </th>
                    <td className="py-2 text-gray-900 dark:text-gray-200">
                      {String(value).length > 100
                        ? String(value).substring(0, 97) + '...'
                        : String(value)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
