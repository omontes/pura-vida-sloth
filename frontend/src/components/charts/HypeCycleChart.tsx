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

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useTheme } from '@/contexts/ThemeContext';
import {
  generateHypeCyclePath,
  PHASE_COLORS,
  PHASE_SEPARATORS,
  PHASE_LABELS,
} from '@/utils/hypeCycleCurve';
import type { Technology } from '@/types/hypeCycle';

interface HypeCycleChartProps {
  technologies: Technology[];
  onTechnologyClick: (techId: string) => void;
  width?: number;
  height?: number;
}

// Label node for force simulation
interface LabelNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  nodeX: number;       // Fixed X position (on curve)
  nodeY: number;       // Fixed Y position (on curve)
  preferredY: number;  // Preferred Y position (above node)
  width: number;       // Label bounding box width
  height: number;      // Label bounding box height
  phase: string;       // For styling
}

export default function HypeCycleChart({
  technologies,
  onTechnologyClick,
  width = 1200,
  height = 700,
}: HypeCycleChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { theme } = useTheme();

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
        .attr('stroke-dasharray', '8 4');
    });

    // 3. Draw phase labels (theme-aware)
    PHASE_LABELS.forEach(({ name, x }) => {
      const lines = name.split('\n');
      const textGroup = svg
        .append('text')
        .attr('x', xScale(x))
        .attr('y', height - 100)
        .attr('text-anchor', 'middle')
        .style('fill', theme.colors.text.secondary)
        .style('font-size', '14px')
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
      .attr('x', -(height / 2))
      .attr('y', 50)
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.chart.axisText)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .text('Market Expectations');

    // 5. Draw X-axis label (theme-aware)
    svg
      .append('text')
      .attr('x', width / 2)
      .attr('y', height - 35)
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.chart.axisText)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .text('Technology Maturity Timeline');

    // 6. Draw technology nodes ON the curve
    const nodeGroups = svg
      .selectAll('.tech-node')
      .data(technologies)
      .enter()
      .append('g')
      .attr('class', 'tech-node cursor-pointer')
      .attr('transform', (d) => {
        const x = xScale(d.chart_x);
        const y = getYForX(d.chart_x); // Y from curve, NOT d.chart_y
        return `translate(${x}, ${y})`;
      })
      .on('click', (_event, d) => {
        _event.stopPropagation();
        onTechnologyClick(d.id);
      })
      .on('mouseenter', function () {
        // Hover effect - scale node
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', 14);
      })
      .on('mouseleave', function () {
        // Restore original size
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', 12);
      });

    // Node circles (uniform size, theme-aware stroke)
    nodeGroups
      .append('circle')
      .attr('r', 12)
      .attr('fill', (d) => PHASE_COLORS[d.phase] || '#8892a6')
      .attr('stroke', theme.colors.chart.nodeStroke)
      .attr('stroke-width', 2.5)
      .style('cursor', 'pointer');

    // 7. Smart Label Positioning with Collision Avoidance
    // Create temporary labels to measure dimensions
    const tempLabels = svg
      .selectAll('.temp-label')
      .data(technologies)
      .enter()
      .append('text')
      .attr('class', 'temp-label')
      .style('font-size', '12px')
      .style('font-weight', '700')
      .style('opacity', 0)
      .text((d) => d.name);

    // Measure label dimensions and create label nodes
    const labelNodes: LabelNode[] = [];
    tempLabels.each(function (d) {
      const bbox = (this as SVGTextElement).getBBox();
      const nodeX = xScale(d.chart_x);
      const nodeY = getYForX(d.chart_x);

      labelNodes.push({
        id: d.id,
        name: d.name,
        nodeX: nodeX,
        nodeY: nodeY,
        preferredY: nodeY - 35, // Prefer 35px above node
        width: bbox.width + 8,
        height: bbox.height + 4,
        phase: d.phase,
        x: nodeX,
        y: nodeY - 35,
        fx: nodeX, // Fix X position (don't drift horizontally)
      });
    });

    // Remove temporary labels
    tempLabels.remove();

    // Custom clamp force to keep labels within chart bounds
    const forceClamp = (minY: number, maxY: number) => {
      let nodes: LabelNode[];

      const force = () => {
        nodes.forEach((n) => {
          const halfHeight = n.height / 2;
          if (n.y !== undefined) {
            if (n.y - halfHeight < minY) n.y = minY + halfHeight;
            if (n.y + halfHeight > maxY) n.y = maxY - halfHeight;
          }
        });
      };

      force.initialize = (n: LabelNode[]) => (nodes = n);
      return force;
    };

    // Run force simulation for collision avoidance
    const simulation = d3
      .forceSimulation(labelNodes)
      .force(
        'collide',
        d3
          .forceCollide<LabelNode>()
          .radius((d) => Math.max(d.width, d.height) / 2 + 3)
          .strength(0.8)
          .iterations(4)
      )
      .force(
        'y',
        d3
          .forceY<LabelNode>((d) => d.preferredY)
          .strength(0.15)
      )
      .force('clamp', forceClamp(70, height - 150))
      .stop();

    // Run simulation synchronously (300 ticks for stable layout)
    for (let i = 0; i < 300; i++) {
      simulation.tick();
    }

    // Render leader lines (polylines connecting labels to nodes)
    svg
      .selectAll('.leader-line')
      .data(labelNodes.filter((d) => Math.abs((d.y || 0) - d.nodeY) > 10))
      .enter()
      .append('polyline')
      .attr('class', 'leader-line')
      .attr('points', (d) => {
        const midY = ((d.y || 0) + d.nodeY) / 2;
        return `${d.nodeX},${d.nodeY} ${d.nodeX},${midY} ${d.x},${d.y}`;
      })
      .attr('fill', 'none')
      .attr('stroke', theme.colors.chart.separator)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.5)
      .style('pointer-events', 'none');

    // Render smart-positioned labels (no background boxes)
    svg
      .selectAll('.tech-label')
      .data(labelNodes)
      .enter()
      .append('text')
      .attr('class', 'tech-label')
      .attr('x', (d) => d.x || 0)
      .attr('y', (d) => (d.y || 0) + 4) // Vertical centering adjustment
      .attr('text-anchor', 'middle')
      .style('fill', theme.colors.text.primary)
      .style('font-size', '12px')
      .style('font-weight', '700')
      .style('pointer-events', 'none')
      .text((d) => d.name);

    // Tooltips
    nodeGroups
      .append('title')
      .text(
        (d) =>
          `${d.name}\nPhase: ${d.phase} (${(d.phase_confidence * 100).toFixed(0)}% confidence)\nHype Score: ${d.scores.hype.toFixed(1)}\n\n${d.summary}`
      );
  }, [technologies, onTechnologyClick, width, height, theme]);

  return (
    <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
        Hype Cycle for Emerging Tech, 2025
      </h2>
      <svg ref={svgRef} width={width} height={height} />

      {/* Phase Legend */}
      <div className="mt-6 flex items-center justify-center gap-6">
        {Object.entries(PHASE_COLORS).map(([phase, color]) => (
          <div key={phase} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {phase}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
