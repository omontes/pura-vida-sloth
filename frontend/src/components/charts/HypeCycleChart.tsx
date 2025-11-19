/**
 * Hype Cycle Chart Component
 *
 * D3.js visualization of Gartner Hype Cycle with technologies positioned ON the curve line.
 * Features:
 * - Custom Bezier curve matching Gartner style
 * - 5 phase separators (vertical dashed lines)
 * - Phase labels with color coding
 * - Interactive nodes with hover effects
 * - Click to drill down to evidence
 */

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useTheme } from '@/contexts/ThemeContext';
import Card, { CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import {
  generateHypeCyclePath,
  PHASE_COLORS,
  PHASE_SEPARATORS,
  PHASE_LABELS,
  validateChartPosition,
} from '@/utils/hypeCycleCurve';
import {
  type LabelNode,
  CurveDistanceCache,
  calculateSmartPreferredPosition,
  forceCurveRepulsion,
  forceNodeRepulsion,
  calculateLabelAnchor,
  wrapText,
  calculateWrappedTextDimensions,
} from '@/utils/labelPositioning';
import type { Technology } from '@/types/hypeCycle';

interface HypeCycleChartProps {
  technologies: Technology[];
  onTechnologyClick: (techId: string) => void;
  width?: number;
  height?: number;
}

// Always use full-size chart with horizontal scroll on smaller devices
const getResponsiveDimensions = () => {
  return { width: 1100, height: 700 };
};

export default function HypeCycleChart({
  technologies,
  onTechnologyClick,
  width: propWidth,
  height: propHeight,
}: HypeCycleChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { theme } = useTheme();

  // Responsive dimensions state
  const [dimensions, setDimensions] = useState(() => {
    // Use prop dimensions if provided, otherwise calculate responsive
    if (propWidth && propHeight) {
      return { width: propWidth, height: propHeight };
    }
    return getResponsiveDimensions();
  });

  const { width, height } = dimensions;

  // Handle responsive resize (only if no prop dimensions provided)
  useEffect(() => {
    if (propWidth && propHeight) return; // Skip if dimensions are provided as props

    const handleResize = () => {
      setDimensions(getResponsiveDimensions());
    };

    // Add resize listener
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, [propWidth, propHeight]);

  useEffect(() => {
    if (!svgRef.current || !technologies.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Generate curve path and utility functions
    const { pathString, xScale, getYForX } = generateHypeCyclePath(
      width,
      height
    );

    // 1. Draw hype cycle curve (theme-aware)
    svg
      .append('path')
      .attr('d', pathString)
      .attr('stroke', theme.colors.chart.curve)
      .attr('stroke-width', 4)
      .attr('fill', 'none');

    // 2. Draw phase separators (theme-aware)
    PHASE_SEPARATORS.forEach((x) => {
      svg
        .append('line')
        .attr('x1', xScale(x))
        .attr('x2', xScale(x))
        .attr('y1', 60)
        .attr('y2', height - 140)
        .attr('stroke', theme.colors.chart.separator)
        .attr('stroke-width', 2)
        .attr('opacity', 0.3)
        .attr('stroke-dasharray', '8 4');
    });

    // 3. Draw phase labels (theme-aware)
    PHASE_LABELS.forEach(({ name, x }) => {
      const lines = name.split('\n');
      const textGroup = svg
        .append('text')
        .attr('x', xScale(x))
        .attr('y', height - 110) // Moved from -110 to -130 for cleaner separation
        .attr('text-anchor', 'middle')
        .style('fill', theme.colors.text.secondary)
        .style('font-size', '12px')
        .style('font-weight', '600');

      lines.forEach((line, i) => {
        textGroup
          .append('tspan')
          .attr('x', xScale(x))
          .attr('dy', i === 0 ? 0 : 16)
          .text(line);
      });
    });

    // 4. Draw Y-axis label (theme-aware)
    svg
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(height / 3))
      .attr('y', 30)
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.chart.axisText)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .text('Market Expectations');

    // 5. Draw X-axis label (theme-aware)
    svg
      .append('text')
      .attr('x', width / 2)
      .attr('y', height - 10)
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.chart.axisText)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .text('Technology Maturity Timeline');

    // 5b. Draw X-axis horizontal line
    svg
      .append('line')
      .attr('x1', 80)
      .attr('x2', width - 80)
      .attr('y1', height - 70)
      .attr('y2', height - 70)
      .attr('stroke', theme.colors.chart.separator)
      .attr('stroke-width', 2)
      .attr('opacity', 0.4);

    // SMART LABEL CULLING: Calculate which nodes should show labels based on density
    // Group technologies by phase
    const techsByPhase = technologies.reduce((acc, tech) => {
      if (!acc[tech.phase]) acc[tech.phase] = [];
      acc[tech.phase].push(tech);
      return acc;
    }, {} as Record<string, typeof technologies>);

    // Calculate label visibility per phase (density-adaptive)
    const labelVisibility = new Map<string, boolean>();

    Object.entries(techsByPhase).forEach(([_phase, techs]) => {
      const count = techs.length;

      // Density-adaptive thresholds
      let showPercentage = 1.0; // Default: show all
      if (count > 12) showPercentage = 0.4;       // >12 nodes: show top 40%
      else if (count >= 9) showPercentage = 0.5;  // 9-12 nodes: show top 50%
      else if (count >= 6) showPercentage = 0.7;  // 6-8 nodes: show top 70%
      // <= 5 nodes: show all (100%)

      const numToShow = Math.max(1, Math.ceil(count * showPercentage));

      // GREEDY SPATIAL SELECTION: Balance importance with spatial distribution
      // Calculate importance scores for all nodes
      const candidatesWithScores = techs.map((tech) => {
        const normalizedHype = tech.scores.hype / 100; // 0-1 range
        const importanceScore =
          tech.phase_confidence * 0.6 + normalizedHype * 0.4;
        return { tech, importanceScore };
      });

      const selected: typeof candidatesWithScores = [];
      const remaining = [...candidatesWithScores];

      // Distance boost factor - controls spacing vs importance balance
      // Higher = more spread, Lower = more importance-driven
      const DISTANCE_BOOST_FACTOR = 0.4;

      // Greedy selection loop
      for (let i = 0; i < numToShow && remaining.length > 0; i++) {
        if (i === 0) {
          // First selection: pure importance (highest score wins)
          remaining.sort((a, b) => b.importanceScore - a.importanceScore);
          selected.push(remaining[0]);
          remaining.splice(0, 1);
        } else {
          // Subsequent selections: apply distance penalty to avoid clustering
          const scoredRemaining = remaining.map((candidate) => {
            // Calculate minimum distance to any already-selected label
            let minDistance = Infinity;
            for (const sel of selected) {
              const distance = Math.abs(candidate.tech.chart_x - sel.tech.chart_x);
              minDistance = Math.min(minDistance, distance);
            }

            // Normalize distance (0-1 range within phase width ~0.2)
            const normalizedDistance = Math.min(minDistance / 0.2, 1.0);

            // Boost score based on distance (farther = higher boost)
            const adjustedScore =
              candidate.importanceScore *
              (1 + DISTANCE_BOOST_FACTOR * normalizedDistance);

            return { ...candidate, adjustedScore };
          });

          // Select node with highest adjusted score
          scoredRemaining.sort((a, b) => b.adjustedScore! - a.adjustedScore!);
          const winner = scoredRemaining[0];
          selected.push(winner);

          // Remove from remaining candidates
          const winnerIndex = remaining.findIndex(
            (r) => r.tech.id === winner.tech.id
          );
          remaining.splice(winnerIndex, 1);
        }
      }

      // Mark selected technologies for label visibility
      selected.forEach((item) => {
        labelVisibility.set(item.tech.id, true);
      });
      remaining.forEach((item) => {
        labelVisibility.set(item.tech.id, false);
      });
    });

    // ZIG-ZAG ALTERNATION: Determine preferred side (above/below) for VISIBLE labels only
    // This ensures a perfect railroad track pattern for dense phases
    const preferredSideMap = new Map<string, 'above' | 'below' | 'auto'>();

    Object.entries(techsByPhase).forEach(([_phase, techs]) => {
      // Filter to ONLY visible labels (the key insight!)
      const visibleTechs = techs.filter(tech => labelVisibility.get(tech.id));
      const visibleCount = visibleTechs.length;

      // Only apply zig-zag alternation for phases with 6+ VISIBLE labels
      if (visibleCount >= 5) {
        // Sort visible labels by horizontal position to create consistent alternation
        const sortedVisibleTechs = [...visibleTechs].sort((a, b) => a.chart_x - b.chart_x);

        // Alternate ONLY the visible labels: even = above, odd = below
        // This creates perfect railroad track pattern!
        sortedVisibleTechs.forEach((tech, index) => {
          preferredSideMap.set(tech.id, index % 2 === 0 ? 'above' : 'below');
        });
      } else {
        // For sparse phases, use default auto behavior (prefer above)
        visibleTechs.forEach((tech) => {
          preferredSideMap.set(tech.id, 'auto');
        });
      }
    });

    // 6. Draw technology nodes ON the curve
    const nodeGroups = svg
      .selectAll('.tech-node')
      .data(technologies)
      .enter()
      .append('g')
      .attr('class', 'tech-node cursor-pointer')
      .attr('transform', (d) => {
        // Validate: ensure chart_x matches phase boundaries
        const validatedX = validateChartPosition(d.phase, d.chart_x, d.phase_position);
        const x = xScale(validatedX);
        const y = getYForX(validatedX); // Y from curve, NOT d.chart_y
        return `translate(${x}, ${y})`;
      })
      .on('click', (_event, d) => {
        _event.stopPropagation();
        onTechnologyClick(d.id);
      })
      .on('mouseenter', function (_event, d) {
        // Hover effect - scale node
        d3.select(this)
          .select('circle')
          .transition()
          .duration(100)
          .attr('r', 14);

        // For unlabeled nodes, show temporary floating label on hover
        if (!labelVisibility.get(d.id)) {
          const validatedX = validateChartPosition(d.phase, d.chart_x, d.phase_position);
          const nodeX = xScale(validatedX);
          const nodeY = getYForX(validatedX);

          // Add temporary label with background
          const tempLabelGroup = svg
            .append('g')
            .attr('class', 'temp-label-group')
            .style('opacity', 0)
            .style('pointer-events', 'none');

          // Add background rectangle
          const text = tempLabelGroup
            .append('text')
            .attr('class', 'temp-label-text')
            .attr('x', nodeX)
            .attr('y', nodeY - 250)
            .attr('text-anchor', 'middle')
            .style('fill', theme.colors.text.primary)
            .style('font-size', '11px')
            .style('font-weight', '700')
            .text(d.name);

          const bbox = (text.node() as SVGTextElement).getBBox();
          tempLabelGroup
            .insert('rect', 'text')
            .attr('x', bbox.x - 4)
            .attr('y', bbox.y - 2)
            .attr('width', bbox.width + 8)
            .attr('height', bbox.height + 4)
            .attr('fill', theme.colors.chart.labelBackground)
            .attr('stroke', theme.colors.chart.labelBorder)
            .attr('stroke-width', 1)
            .attr('rx', 3);

          tempLabelGroup.transition().duration(200).style('opacity', 1);
        }
      })
      .on('mouseleave', function (_event, d) {
        // Restore original size based on label visibility
        const originalSize = labelVisibility.get(d.id) ? 12 : 10;
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', originalSize);

        // Remove temporary label for unlabeled nodes
        if (!labelVisibility.get(d.id)) {
          svg
            .selectAll('.temp-label-group')
            .transition()
            .duration(200)
            .style('opacity', 0)
            .remove();
        }
      });

    // Node circles (conditional size/opacity based on label visibility)
    nodeGroups
      .append('circle')
      .attr('r', (d) => labelVisibility.get(d.id) ? 12 : 10) // Labeled: 12px, Unlabeled: 10px
      .attr('fill', (d) => PHASE_COLORS[d.phase] || '#8892a6')
      .attr('fill-opacity', (d) => labelVisibility.get(d.id) ? 1.0 : 0.6) // Labeled: full, Unlabeled: 60%
      .attr('stroke', theme.colors.chart.nodeStroke)
      .attr('stroke-width', 2.5)
      .style('cursor', 'pointer');

    // 7. OPTIMIZED: Intelligent Curve-Aware Label Positioning
    // Create path element for distance calculations
    const pathElement = document.createElementNS(
      'http://www.w3.org/2000/svg',
      'path'
    );
    pathElement.setAttribute('d', pathString);

    // OPTIMIZATION: Create distance cache once (10px sampling vs 5px)
    const curveCache = new CurveDistanceCache(pathElement,);

    // Pre-compute wrapped lines for all technologies (multi-line text wrapping)
    const wrappedLines = technologies.map((tech) => wrapText(tech.name, 16)); // Increased from 13 to 16 for better readability

    // Measure label dimensions and calculate smart positions using radial sampling
    const labelNodes: LabelNode[] = [];
    const chartBounds = { minY: -100, maxY: height - 100 }; // Increased bottom space to allow below-curve labels (railroad track pattern)

    technologies.forEach((d, i) => {
      // Calculate dimensions from wrapped lines (no need for temporary rendering)
      const lines = wrappedLines[i];
      const { width: labelWidth, height: labelHeight } = calculateWrappedTextDimensions(
        lines,
        10,   // fontSize
        700,  // fontWeight
        6.2,  // charWidth
        1.3   // lineHeight
      );

      // Validate: ensure chart_x matches phase boundaries
      const validatedX = validateChartPosition(d.phase, d.chart_x, d.phase_position);
      const nodeX = xScale(validatedX);
      const nodeY = getYForX(validatedX);

      // Get preferred side for this technology (zig-zag pattern)
      const preferredSide = preferredSideMap.get(d.id) || 'auto';

      // OPTIMIZATION: Use cached distance calculation with zig-zag alternation
      const smartPosition = calculateSmartPreferredPosition(
        nodeX,
        nodeY,
        labelWidth,
        labelHeight,
        curveCache,
        labelNodes.map((l) => ({
          x: l.x || 0,
          y: l.y || 0,
          width: l.width,
          height: l.height,
        })),
        chartBounds,
        preferredSide  // Pass preferred side for zig-zag alternation
      );

      labelNodes.push({
        id: d.id,
        name: d.name,
        nodeX: nodeX,
        nodeY: nodeY,
        preferredY: smartPosition.y,
        width: labelWidth,
        height: labelHeight,
        phase: d.phase,
        x: smartPosition.x,
        y: smartPosition.y,
      });
    });

    // Custom clamp force to keep labels within chart bounds
    const forceClamp = (minY: number, maxY: number) => {
      let nodes: LabelNode[];

      const force = () => {
        nodes.forEach((n) => {
          const halfHeight = n.height / 2;
          if (n.y !== undefined) {
            if (n.y - halfHeight < minY) n.y = minY + halfHeight-50;
            if (n.y + halfHeight > maxY) n.y = maxY - halfHeight;
          }
        });
      };

      force.initialize = (n: LabelNode[]) => (nodes = n);
      return force;
    };

    // OPTIMIZED: Run force simulation optimized for narrower multi-line labels
    const simulation = d3
      .forceSimulation(labelNodes)
      .force(
        'collide',
        d3
          .forceCollide<LabelNode>()
          .radius((d) => Math.max(d.width, d.height) / 3 + 6) // Tighter collision detection for multi-line labels
          .strength(0.75) // Reduced from 0.75 - allow some tolerance for better distribution
          .iterations(5) // Better convergence for complex label layouts
      )
      .force('curve-repulsion', forceCurveRepulsion(pathElement, 20)) // Increased from 24 - stronger separation from curve
      .force('node-repulsion', forceNodeRepulsion(50)) // Prevent labels from overlapping their anchor nodes
      .force(
        'y',
        d3
          .forceY<LabelNode>((d) => d.preferredY)
          .strength(0.12) // Increased from 0.12 - keep labels at smart positions, prevent clustering
      )
      .force('clamp', forceClamp(50, height - 140)) // Allow labels to use top space (down to y=50)
      .alphaDecay(1.5) // Faster convergence (default: 0.028)
      .stop();

    // OPTIMIZED: Reduced ticks with early stopping (300 → 150 max, ~80 average)
    const maxTicks = 150;
    const velocityThreshold = 0.01;

    for (let i = 0; i < maxTicks; i++) {
      simulation.tick();

      // Early stopping: check if labels have stabilized
      if (i > 50) {
        const maxVelocity = Math.max(
          ...labelNodes.map((n) =>
            Math.sqrt((n.vx || 0) ** 2 + (n.vy || 0) ** 2)
          )
        );

        if (maxVelocity < velocityThreshold) {
          console.log(`Label positioning converged early at tick ${i}`);
          break;
        }
      }
    }

    // Render diagonal leader lines (connecting labels to nodes)
    svg
      .selectAll('.leader-line')
      .data(
        labelNodes.filter((d) => {
          // Only show leader lines for visible labels
          if (!labelVisibility.get(d.id)) return false;

          const dx = Math.abs((d.x || 0) - d.nodeX);
          const dy = Math.abs((d.y || 0) - d.nodeY);
          const distance = Math.sqrt(dx * dx + dy * dy);
          return distance > 30; // Only show if label significantly displaced
        })
      )
      .enter()
      .append('line')
      .attr('class', 'leader-line')
      .attr('x1', (d) => d.nodeX)
      .attr('y1', (d) => {
        // Start from edge of node circle, not center
        const dy = (d.y || 0) - d.nodeY;
        const distance = Math.sqrt(
          Math.pow((d.x || 0) - d.nodeX, 2) + Math.pow(dy, 2)
        ) || 1;
        return d.nodeY + (dy / distance) * 12; // 12 = node radius
      })
      .attr('x2', (d) => calculateLabelAnchor(d).x)
      .attr('y2', (d) => calculateLabelAnchor(d).y)
      .attr('stroke', theme.colors.chart.separator)
      .attr('stroke-width', 1)
       .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.9)
      .style('pointer-events', 'none');

    // Render smart-positioned labels with multi-line support (only visible labels)
    svg
      .selectAll('.tech-label')
      .data(labelNodes.filter((d) => labelVisibility.get(d.id)))
      .enter()
      .append('text')
      .attr('class', 'tech-label')
      .attr('x', (d) => d.x || 0)
      .attr('y', (d) => (d.y || 0) + 5) // Vertical centering adjustment
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.text.primary)
      .style('font-size', '10px')
      .style('font-weight', '700')
      .style('pointer-events', 'none')
      .each(function (d) {
        const lines = wrapText(d.name, 16); // Use the name from labelNode data, not filtered index!
        const textElement = d3.select(this);

        // Add first line as main text content
        textElement.text(lines[0] || '');

        // Add remaining lines as tspan elements
        lines.slice(1).forEach((line) => {
          textElement
            .append('tspan')
            .attr('x', d.x || 0) // Re-center each line
            .attr('dy', '13px') // Line height: 1.3 × 10px font size
            .text(line);
        });
      });

    // Tooltips
    nodeGroups
      .append('title')
      .text(
        (d) =>
          `${d.name}\nPhase: ${d.phase} (${(d.phase_confidence * 100).toFixed(0)}% confidence)\nHype Score: ${d.scores.hype.toFixed(1)}\n\n${d.summary}`
      );
  }, [technologies, onTechnologyClick, width, height, theme]);

  return (
    <Card elevation="raised" padding="spacious" className="w-full">
      <CardHeader>
        <CardTitle as="h2" className="text-4xl">Technology Hype Cycle for EVTOL & Advanced Air Mobility, 2025</CardTitle>
        <CardDescription>
          Multi-source intelligence positioning across the adoption lifecycle. Labels shown for highest confidence technologies (hover any node to reveal name). Click any technology on the chart to update the knowledge graph below.
        </CardDescription>
      </CardHeader>

      {/* Chart container with horizontal scroll on smaller devices */}
      <div className="overflow-x-auto">
        <svg ref={svgRef} width={width} height={height} className="mx-auto" />
      </div>

      {/* Phase Legend */}
      <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800">
        <div className="flex flex-wrap items-center justify-center gap-6">
          {Object.entries(PHASE_COLORS).map(([phase, color]) => (
            <div key={phase} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full shadow-sm"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {phase}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
