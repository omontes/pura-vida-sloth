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

        // Highlight label background (theme-aware)
        d3.select(this)
          .select('rect.label-bg')
          .transition()
          .duration(200)
          .attr('fill', theme.colors.background.primary)
          .attr('stroke', theme.colors.interactive.secondary);
      })
      .on('mouseleave', function () {
        // Restore original size
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', 12);

        // Restore label background (theme-aware)
        d3.select(this)
          .select('rect.label-bg')
          .transition()
          .duration(200)
          .attr('fill', theme.colors.chart.labelBackground)
          .attr('stroke', theme.colors.chart.labelBorder);
      });

    // Node circles (uniform size, theme-aware stroke)
    nodeGroups
      .append('circle')
      .attr('r', 12)
      .attr('fill', (d) => PHASE_COLORS[d.phase] || '#8892a6')
      .attr('stroke', theme.colors.chart.nodeStroke)
      .attr('stroke-width', 2.5)
      .style('cursor', 'pointer');

    // Label background (theme-aware)
    nodeGroups
      .append('rect')
      .attr('class', 'label-bg')
      .attr('x', (d) => {
        const textLength = d.name.length * 6.5;
        return -textLength / 2 - 6;
      })
      .attr('y', -30)
      .attr('width', (d) => d.name.length * 6.5 + 12)
      .attr('height', 20)
      .attr('fill', theme.colors.chart.labelBackground)
      .attr('stroke', theme.colors.chart.labelBorder)
      .attr('stroke-width', 1)
      .attr('rx', 4)
      .attr('ry', 4);

    // Node labels (theme-aware)
    nodeGroups
      .append('text')
      .attr('y', -16)
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
