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
import { Network } from 'vis-network';
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
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [retryCount, setRetryCount] = useState(0);
  const networkRef = useRef<Network | null>(null);

  // Edge tooltip state
  const [hoveredEdge, setHoveredEdge] = useState<VisEdge | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState(false);

  // Node panel state
  const [expandedDescription, setExpandedDescription] = useState(false);

  // Use theme context for dark/light mode
  const { themeMode } = useTheme();
  const isDarkMode = themeMode === 'dark';

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setLoadingMessage(technologyId ? 'Loading technology subgraph...' : 'Loading full knowledge graph...');

    // Get API URL from environment (supports both dev and production)
    const API_URL = import.meta.env.VITE_API_URL || '';
    const endpoint = `${API_URL}/api/neo4j/subgraph`;

    // Create AbortController for timeout (90 seconds to handle Render cold starts)
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 90000);

    // Enhanced loading messages with progressive updates
    const message10s = setTimeout(() => {
      setLoadingMessage('Still loading... Backend may be waking up (this can take 30-50 seconds on first request)');
    }, 10000);

    const message30s = setTimeout(() => {
      setLoadingMessage('Backend is warming up... Almost there (typically takes 30-50 seconds after sleep)');
    }, 30000);

    const message60s = setTimeout(() => {
      setLoadingMessage('Taking longer than usual... Please wait a few more seconds');
    }, 60000);

    // Fetch subgraph from real Neo4j API
    // If technologyId is null, fetches full graph with all technologies
    // If technologyId is provided, fetches filtered subgraph for that technology
    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tech_id: technologyId }),
      signal: abortController.signal,
    })
      .then((res) => {
        clearTimeout(timeoutId);
        clearTimeout(message10s);
        clearTimeout(message30s);
        clearTimeout(message60s);

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
        setRetryCount(0); // Reset retry count on success
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        clearTimeout(message10s);
        clearTimeout(message30s);
        clearTimeout(message60s);

        console.error('Error loading Neo4j subgraph:', err);

        // Distinguish timeout from other errors
        if (err.name === 'AbortError') {
          setError('Request timed out. The backend server may be experiencing issues or is taking too long to wake up from sleep. Please try again.');
        } else {
          setError(err.message || 'Failed to load graph. The backend may be starting up.');
        }
        setIsLoading(false);
      });

    // Cleanup function
    return () => {
      clearTimeout(timeoutId);
      clearTimeout(message10s);
      clearTimeout(message30s);
      clearTimeout(message60s);
      abortController.abort();
    };
  }, [technologyId, retryCount]); // Add retryCount to dependencies to trigger retry

  // Event handlers for edges and nodes
  const events = {
    // Edge hover tooltips
    hoverEdge: (event: any) => {
      const edgeId = event.edge;
      const edge = graphData.edges.find((e) => e.id === edgeId);

      if (edge && event.pointer && event.pointer.DOM) {
        setHoveredEdge(edge);
        setTooltipPosition({ x: event.pointer.DOM.x, y: event.pointer.DOM.y });
        setExpandedEvidence(false); // Reset expansion when hovering new edge
      }
    },
    blurEdge: () => {
      setHoveredEdge(null);
      setTooltipPosition(null);
      setExpandedEvidence(false);
    },

    // Node click handler
    click: (event: any) => {
      if (event.nodes.length > 0) {
        const nodeId = event.nodes[0];
        const node = graphData.nodes.find((n) => n.id === nodeId);

        if (node) {
          setSelectedNode(node);
          setExpandedDescription(false);
        }
      } else {
        // Clicked on empty space - clear selection
        setSelectedNode(null);
      }
    },
  };

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
          getNetwork={(network: Network) => {
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
          <div className="text-center max-w-md px-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              {loadingMessage}
            </p>
            <p className="text-gray-500 dark:text-gray-500 text-xs mt-2">
              Free tier backend may take 30-50 seconds to wake from sleep
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
            <p className="text-gray-600 dark:text-gray-500 text-sm mb-4">{error}</p>
            <button
              onClick={() => setRetryCount(prev => prev + 1)}
              className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white rounded-lg font-medium transition-colors duration-200 shadow-md hover:shadow-lg"
            >
              🔄 Retry
            </button>
            <p className="text-gray-500 dark:text-gray-600 text-xs mt-4">
              Backend may need 30-50 seconds to wake from sleep
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
        <div className="absolute bottom-20 left-4 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-w-md max-h-[500px] overflow-hidden flex flex-col">
          {/* Header: doc_type/group (PROMINENT) + close button */}
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-start justify-between flex-shrink-0">
            <div className="flex-1 min-w-0">
              {/* doc_type - LARGE and BOLD */}
              <div className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">
                {selectedNode.properties.doc_type || selectedNode.group}
              </div>
              {/* Node label - subtitle */}
              <div className="text-xs text-gray-500 dark:text-gray-400 break-words max-w-full">
                {selectedNode.label}
              </div>
              {/* View Document button */}
              {selectedNode.properties.url && (
                <a
                  href={selectedNode.properties.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs px-3 py-1.5 rounded bg-teal-600 hover:bg-teal-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white font-medium transition"
                >
                  View Document →
                </a>
              )}
            </div>
            <button
              onClick={() => {
                setSelectedNode(null);
                setExpandedDescription(false);
              }}
              className="ml-3 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-lg leading-none flex-shrink-0"
            >
              ✕
            </button>
          </div>

          {/* Scrollable content */}
          <div className="overflow-y-auto flex-1">
            {/* Summary - For documents */}
            {selectedNode.properties.summary && (
              <div className="px-4 pt-4 pb-3">
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  Summary
                </div>
                <div
                  className="text-sm leading-relaxed text-gray-700 dark:text-gray-300"
                  style={{
                    wordBreak: 'break-word',
                    overflowWrap: 'anywhere',
                    hyphens: 'auto'
                  }}
                >
                  {selectedNode.properties.summary}
                </div>
              </div>
            )}

            {/* Description - Main Content */}
            {selectedNode.properties.description && (
              <div className="px-4 pb-4">
                <div
                  className="text-sm leading-relaxed text-gray-700 dark:text-gray-300"
                  style={{
                    wordBreak: 'break-word',
                    overflowWrap: 'anywhere',
                    hyphens: 'auto'
                  }}
                >
                  {expandedDescription || String(selectedNode.properties.description).length <= 200
                    ? selectedNode.properties.description
                    : `${String(selectedNode.properties.description).substring(0, 200)}...`}
                  {String(selectedNode.properties.description).length > 200 && (
                    <button
                      onClick={() => setExpandedDescription(!expandedDescription)}
                      className="block mt-2 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 underline"
                    >
                      {expandedDescription ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Metadata - Filtered, Sorted, and Formatted */}
            <div className="px-4 pb-3 pt-2 space-y-1 border-t border-gray-200 dark:border-gray-700">
              {Object.entries(selectedNode.properties)
                .filter(([key]) => {
                  // Exclude technical and already-shown fields
                  return (
                    !key.toLowerCase().includes('embedding') &&
                    !key.toLowerCase().includes('search_corpus') &&
                    key !== 'description' &&
                    key !== 'summary' &&  // Exclude summary (shown above)
                    key !== 'doc_type' &&
                    key !== 'url' &&
                    !key.startsWith('community_')
                  );
                })
                .sort(([keyA], [keyB]) => {
                  // Priority order for important fields
                  const priority: Record<string, number> = {
                    'citation_count': 1,
                    'quality_score': 2,
                    'degree_centrality': 3,
                    'aliases': 4,
                  };
                  const priorityA = priority[keyA] || 999;
                  const priorityB = priority[keyB] || 999;
                  return priorityA - priorityB;
                })
                .map(([key, value]) => {
                  // Format key for display
                  const displayKey = key
                    .split('_')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');

                  // Format value
                  let displayValue = value;
                  if (Array.isArray(value)) {
                    displayValue = value.join(', ');
                  } else if (typeof value === 'number') {
                    displayValue = value.toFixed(2);
                  }

                  return (
                    <div key={key} className="flex justify-between items-start gap-4 text-xs">
                      <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">{displayKey}:</span>
                      <span
                        className="text-gray-700 dark:text-gray-300 text-right"
                        style={{
                          wordBreak: 'break-word',
                          overflowWrap: 'anywhere'
                        }}
                      >
                        {String(displayValue).length > 100
                          ? String(displayValue).substring(0, 97) + '...'
                          : String(displayValue)}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Edge Tooltip (appears on hover) */}
      {hoveredEdge && hoveredEdge.properties && tooltipPosition && (
        <div
          className="fixed z-50 pointer-events-auto"
          style={{
            left: `${tooltipPosition.x + 8}px`,
            top: `${tooltipPosition.y + 8}px`,
            minWidth: '320px',
            maxWidth: '420px',
          }}
        >
          <div className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg overflow-hidden">
            {/* Simple Header: relation_type + confidence */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <span className="text-base font-bold text-gray-900 dark:text-gray-100">
                {hoveredEdge.properties.relation_type || hoveredEdge.label}
              </span>
              {hoveredEdge.properties.evidence_confidence !== undefined &&
                hoveredEdge.properties.evidence_confidence !== null && (
                  <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                    {(hoveredEdge.properties.evidence_confidence * 100).toFixed(0)}%
                  </span>
                )}
            </div>

            {/* Evidence Text - Main Content */}
            {hoveredEdge.properties.evidence_text && (
              <div className="px-4 py-4">
                <div
                  className="text-sm leading-relaxed text-gray-700 dark:text-gray-300"
                  style={{
                    wordBreak: 'break-word',
                    overflowWrap: 'anywhere',
                    hyphens: 'auto'
                  }}
                >
                  {expandedEvidence || hoveredEdge.properties.evidence_text.length <= 200
                    ? hoveredEdge.properties.evidence_text
                    : `${hoveredEdge.properties.evidence_text.substring(0, 200)}...`}
                  {hoveredEdge.properties.evidence_text.length > 200 && (
                    <button
                      onClick={() => setExpandedEvidence(!expandedEvidence)}
                      className="block mt-2 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 underline"
                    >
                      {expandedEvidence ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Compact Metadata */}
            {(hoveredEdge.properties.role || hoveredEdge.properties.strength || hoveredEdge.properties.doc_ref) && (
              <div className="px-4 pb-3 pt-2 space-y-1 border-t border-gray-200 dark:border-gray-700">
                {hoveredEdge.properties.role && (
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500 dark:text-gray-400">Role:</span>
                    <span className="text-gray-700 dark:text-gray-300">{hoveredEdge.properties.role}</span>
                  </div>
                )}
                {hoveredEdge.properties.strength && (
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500 dark:text-gray-400">Strength:</span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {typeof hoveredEdge.properties.strength === 'number'
                        ? hoveredEdge.properties.strength.toFixed(2)
                        : hoveredEdge.properties.strength}
                    </span>
                  </div>
                )}
                {hoveredEdge.properties.doc_ref && (
                  <div className="flex justify-between items-center gap-2 text-xs">
                    <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">Source:</span>
                    <span className="font-mono text-gray-600 dark:text-gray-400 overflow-hidden text-ellipsis whitespace-nowrap">
                      {hoveredEdge.properties.doc_ref}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
