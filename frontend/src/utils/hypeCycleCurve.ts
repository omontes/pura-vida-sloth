/**
 * Hype Cycle Curve Generator (D3.js)
 *
 * Generates a Gartner-style Hype Cycle curve with precise node positioning.
 * Nodes are positioned ON the curve line (not floating in space).
 */

import * as d3 from 'd3';

export interface HypeCyclePoint {
  phase: string;
  x: number;
  y: number;
}

// Define the 5 phases of the Gartner Hype Cycle
export const HYPE_CYCLE_POINTS: HypeCyclePoint[] = [
  { phase: 'Innovation Trigger', x: 0, y: 0.1 },
  { phase: 'Peak of Inflated Expectations', x: 1.0, y: 0.95 },
  { phase: 'Trough of Disillusionment', x: 2.0, y: 0.25 },
  { phase: 'Slope of Enlightenment', x: 3.5, y: 0.6 },
  { phase: 'Plateau of Productivity', x: 5.0, y: 0.7 },
];

// Phase color palette (matches Gartner style)
export const PHASE_COLORS: Record<string, string> = {
  'Innovation Trigger': '#3b82f6', // Blue
  'Peak of Inflated Expectations': '#ef4444', // Red
  'Trough of Disillusionment': '#f59e0b', // Amber
  'Slope of Enlightenment': '#10b981', // Green
  'Plateau of Productivity': '#6366f1', // Indigo
};

export interface HypeCycleCurveResult {
  pathString: string;
  xScale: d3.ScaleLinear<number, number>;
  yScale: d3.ScaleLinear<number, number>;
  getYForX: (xValue: number) => number;
}

/**
 * Generate Hype Cycle curve path and utility functions
 *
 * @param width - SVG width in pixels
 * @param height - SVG height in pixels
 * @returns Curve path, scales, and positioning functions
 */
export function generateHypeCyclePath(
  width: number,
  height: number
): HypeCycleCurveResult {
  // Create scales with padding for labels
  const xScale = d3
    .scaleLinear()
    .domain([0, 5])
    .range([80, width - 80]);

  const yScale = d3
    .scaleLinear()
    .domain([0, 1])
    .range([height - 120, 60]);

  // Use curveCatmullRom for smooth Gartner-style curve
  // alpha = 0.5 creates a centripetal curve (no self-intersections)
  const line = d3
    .line<HypeCyclePoint>()
    .curve(d3.curveCatmullRom.alpha(0.5))
    .x((d) => xScale(d.x))
    .y((d) => yScale(d.y));

  const pathString = line(HYPE_CYCLE_POINTS) || '';

  // Create a path element for length calculations
  const pathElement = document.createElementNS(
    'http://www.w3.org/2000/svg',
    'path'
  );
  pathElement.setAttribute('d', pathString);

  /**
   * Get Y coordinate for any X position (to place nodes ON curve)
   *
   * Uses binary search along the curve path to find the point
   * where the X coordinate matches the target.
   *
   * @param xValue - X position in data space (0-5)
   * @returns Y position in pixel space
   */
  const getYForX = (xValue: number): number => {
    const totalLength = pathElement.getTotalLength();
    const targetX = xScale(xValue);

    // Binary search for the point on the curve
    let start = 0;
    let end = totalLength;
    let mid = 0;

    // 20 iterations gives us precision within ~0.0001% of path length
    for (let i = 0; i < 20; i++) {
      mid = (start + end) / 2;
      const point = pathElement.getPointAtLength(mid);

      // Found the point (within 1px tolerance)
      if (Math.abs(point.x - targetX) < 1) {
        return point.y;
      }

      // Adjust search bounds
      if (point.x < targetX) {
        start = mid;
      } else {
        end = mid;
      }
    }

    // Return best approximation
    return pathElement.getPointAtLength(mid).y;
  };

  return {
    pathString,
    xScale,
    yScale,
    getYForX,
  };
}

/**
 * Get phase information for a given X position
 *
 * @param xValue - X position (0-5)
 * @returns Phase name and color
 */
export function getPhaseForX(xValue: number): {
  phase: string;
  color: string;
} {
  if (xValue < 1.0) {
    return {
      phase: 'Innovation Trigger',
      color: PHASE_COLORS['Innovation Trigger'],
    };
  } else if (xValue < 2.0) {
    return {
      phase: 'Peak of Inflated Expectations',
      color: PHASE_COLORS['Peak of Inflated Expectations'],
    };
  } else if (xValue < 3.0) {
    return {
      phase: 'Trough of Disillusionment',
      color: PHASE_COLORS['Trough of Disillusionment'],
    };
  } else if (xValue < 4.0) {
    return {
      phase: 'Slope of Enlightenment',
      color: PHASE_COLORS['Slope of Enlightenment'],
    };
  } else {
    return {
      phase: 'Plateau of Productivity',
      color: PHASE_COLORS['Plateau of Productivity'],
    };
  }
}

/**
 * Phase separator X positions (vertical lines)
 */
export const PHASE_SEPARATORS = [1.0, 2.0, 3.0, 4.0];

/**
 * Phase label positions (centered in each phase)
 */
export const PHASE_LABELS = [
  { name: 'Innovation\nTrigger', x: 0.5 },
  { name: 'Peak of Inflated\nExpectations', x: 1.5 },
  { name: 'Trough of\nDisillusionment', x: 2.5 },
  { name: 'Slope of\nEnlightenment', x: 3.5 },
  { name: 'Plateau of\nProductivity', x: 4.5 },
];
