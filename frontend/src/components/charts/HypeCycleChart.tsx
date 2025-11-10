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
  return { width: 1200, height: 700 };
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
        .attr('y', height - 110)
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
      .attr('x', -(height / 2))
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
      .attr('y', height - 40)
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
      .attr('y1', height - 130)
      .attr('y2', height - 130)
      .attr('stroke', theme.colors.chart.separator)
      .attr('stroke-width', 2)
      .attr('opacity', 0.4);

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

    // 7. OPTIMIZED: Intelligent Curve-Aware Label Positioning
    // Create path element for distance calculations
    const pathElement = document.createElementNS(
      'http://www.w3.org/2000/svg',
      'path'
    );
    pathElement.setAttribute('d', pathString);

    // OPTIMIZATION: Create distance cache once (10px sampling vs 5px)
    const curveCache = new CurveDistanceCache(pathElement, 10);

    // Pre-compute wrapped lines for all technologies (multi-line text wrapping)
    const wrappedLines = technologies.map((tech) => wrapText(tech.name, 13));

    // Measure label dimensions and calculate smart positions using radial sampling
    const labelNodes: LabelNode[] = [];
    const chartBounds = { minY: 70, maxY: height - 150 };

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

      // OPTIMIZATION: Use cached distance calculation
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
        chartBounds
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
            if (n.y - halfHeight < minY) n.y = minY + halfHeight;
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
          .radius((d) => Math.max(d.width, d.height) / 2 + 4) // Reduced from 6 (narrower labels need less padding)
          .strength(0.6) // Reduced from 0.8 (weaker repulsion for compact multi-line text)
          .iterations(2) // Reduced from 3 (faster convergence with less collision)
      )
      .force('curve-repulsion', forceCurveRepulsion(pathElement, 18))
      .force(
        'y',
        d3
          .forceY<LabelNode>((d) => d.preferredY)
          .strength(0.12) // Slightly increased from 0.1 (maintain vertical positioning)
      )
      .force('clamp', forceClamp(50, height - 150))
      .alphaDecay(0.05) // Faster convergence (default: 0.028)
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
          const dx = Math.abs((d.x || 0) - d.nodeX);
          const dy = Math.abs((d.y || 0) - d.nodeY);
          const distance = Math.sqrt(dx * dx + dy * dy);
          return distance > 15; // Only show if label significantly displaced
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

    // Render smart-positioned labels with multi-line support
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
      .style('font-size', '10px')
      .style('font-weight', '700')
      .style('pointer-events', 'none')
      .each(function (d, i) {
        const lines = wrappedLines[i];
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
        <CardTitle as="h2" className="text-4xl">Technology Hype Cycle for Emerging Tech, 2025</CardTitle>
        <CardDescription>
          Multi-source intelligence positioning across the adoption lifecycle
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
