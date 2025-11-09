/**
 * Label Positioning Utilities for Hype Cycle Chart
 *
 * Provides intelligent curve-aware label positioning with collision avoidance.
 * Implements radial sampling, curve repulsion forces, and smart anchor points.
 */

import * as d3 from 'd3';

export interface LabelNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  nodeX: number; // Fixed X position (on curve)
  nodeY: number; // Fixed Y position (on curve)
  preferredY: number; // Preferred Y position
  width: number; // Label bounding box width
  height: number; // Label bounding box height
  phase: string; // For styling
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Calculate minimum distance from a rectangular bounding box to the SVG curve
 *
 * @param labelX - Label center X coordinate
 * @param labelY - Label center Y coordinate
 * @param labelWidth - Label width
 * @param labelHeight - Label height
 * @param pathElement - SVG path element reference
 * @returns Minimum distance in pixels
 */
export function getMinDistanceToCurve(
  labelX: number,
  labelY: number,
  labelWidth: number,
  labelHeight: number,
  pathElement: SVGPathElement
): number {
  const totalLength = pathElement.getTotalLength();
  let minDistance = Infinity;

  // Sample the curve at regular intervals (every 5px for performance)
  const sampleInterval = 5;
  const numSamples = Math.ceil(totalLength / sampleInterval);

  for (let i = 0; i <= numSamples; i++) {
    const point = pathElement.getPointAtLength((i / numSamples) * totalLength);

    // Calculate distance from curve point to nearest label edge
    let distance: number;

    // Check if point is inside label box
    if (
      point.x >= labelX - labelWidth / 2 &&
      point.x <= labelX + labelWidth / 2 &&
      point.y >= labelY - labelHeight / 2 &&
      point.y <= labelY + labelHeight / 2
    ) {
      // Curve point is INSIDE label box - zero distance
      return 0;
    }

    // Calculate distance to nearest edge of bounding box
    const dx = Math.max(
      labelX - labelWidth / 2 - point.x,
      0,
      point.x - (labelX + labelWidth / 2)
    );
    const dy = Math.max(
      labelY - labelHeight / 2 - point.y,
      0,
      point.y - (labelY + labelHeight / 2)
    );
    distance = Math.sqrt(dx * dx + dy * dy);

    minDistance = Math.min(minDistance, distance);
  }

  return minDistance;
}

/**
 * Custom D3 force that pushes labels away from the curve
 * Ensures minimum clearance between labels and the Hype Cycle curve
 *
 * @param pathElement - SVG path element for the curve
 * @param minDistance - Minimum clearance in pixels (default: 20)
 * @returns D3 force function
 */
export function forceCurveRepulsion(
  pathElement: SVGPathElement,
  minDistance: number = 20
) {
  let nodes: LabelNode[];
  let curveSamples: Array<{ x: number; y: number }> = [];

  // Pre-sample the curve once for performance
  const initializeCurveSamples = () => {
    const totalLength = pathElement.getTotalLength();
    const sampleInterval = 5;
    const numSamples = Math.ceil(totalLength / sampleInterval);

    curveSamples = [];
    for (let i = 0; i <= numSamples; i++) {
      const point = pathElement.getPointAtLength((i / numSamples) * totalLength);
      curveSamples.push({ x: point.x, y: point.y });
    }
  };

  const force = (alpha: number) => {
    // Initialize samples on first run
    if (curveSamples.length === 0) {
      initializeCurveSamples();
    }

    nodes.forEach((label) => {
      if (!label.x || !label.y) return;

      let closestPoint: { x: number; y: number } | null = null;
      let minDist = Infinity;

      // Find closest point on curve to label center
      for (const sample of curveSamples) {
        const dist = Math.sqrt(
          Math.pow(sample.x - label.x, 2) + Math.pow(sample.y - label.y, 2)
        );
        if (dist < minDist) {
          minDist = dist;
          closestPoint = sample;
        }
      }

      if (!closestPoint) return;

      // Calculate actual distance accounting for label size
      const actualDist = getMinDistanceToCurve(
        label.x,
        label.y,
        label.width,
        label.height,
        pathElement
      );

      // If too close to curve, push away
      if (actualDist < minDistance) {
        const dx = label.x - closestPoint.x;
        const dy = label.y - closestPoint.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        // Repulsion strength increases as distance decreases
        const strength = ((minDistance - actualDist) / minDistance) * alpha;

        // Push label away from curve
        label.vx = (label.vx || 0) + (dx / distance) * strength * 2.0;
        label.vy = (label.vy || 0) + (dy / distance) * strength * 2.0;
      }
    });
  };

  force.initialize = (n: LabelNode[]) => {
    nodes = n;
  };

  return force;
}

/**
 * Calculate optimal label position using radial sampling
 * Tests multiple positions around the node and chooses best one based on:
 * - Maximum distance from curve
 * - Minimum collisions with other labels
 * - Aesthetic preferences (prefer above)
 *
 * @param nodeX - Node X position
 * @param nodeY - Node Y position
 * @param labelWidth - Label width
 * @param labelHeight - Label height
 * @param pathElement - SVG path element
 * @param otherLabels - Already positioned labels
 * @param chartBounds - Chart boundaries
 * @returns Optimal position {x, y, angle}
 */
export function calculateSmartPreferredPosition(
  nodeX: number,
  nodeY: number,
  labelWidth: number,
  labelHeight: number,
  pathElement: SVGPathElement,
  otherLabels: BoundingBox[],
  chartBounds: { minY: number; maxY: number }
): { x: number; y: number; angle: number } {
  // Test angles in degrees (0 = right, -90 = up, 90 = down)
  const testAngles = [
    -90, // Directly above (preferred)
    -75, // Above-right
    -105, // Above-left
    -60, // More to right
    -120, // More to left
    -45, // Far right
    -135, // Far left
    90, // Directly below (for crowded regions)
  ];

  const radiusFromNode = 40; // Distance from node center

  let bestPosition = { x: nodeX, y: nodeY - 35, angle: -90 };
  let bestScore = -Infinity;

  for (const angle of testAngles) {
    const radians = (angle * Math.PI) / 180;
    const candidateX = nodeX + Math.cos(radians) * radiusFromNode;
    const candidateY = nodeY + Math.sin(radians) * radiusFromNode;

    // Check if position is within chart bounds
    const halfHeight = labelHeight / 2;
    if (
      candidateY - halfHeight < chartBounds.minY ||
      candidateY + halfHeight > chartBounds.maxY
    ) {
      continue; // Out of bounds
    }

    // Calculate distance to curve (higher is better)
    const distToCurve = getMinDistanceToCurve(
      candidateX,
      candidateY,
      labelWidth,
      labelHeight,
      pathElement
    );

    // Calculate minimum distance to other labels (higher is better)
    let minDistToOthers = Infinity;
    for (const other of otherLabels) {
      const dx = candidateX - other.x;
      const dy = candidateY - other.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      minDistToOthers = Math.min(minDistToOthers, dist);
    }

    // Composite score: prioritize curve clearance (2x weight)
    const score = distToCurve * 2.0 + minDistToOthers * 1.0;

    // Bonus for "above" positions (aesthetic preference)
    const bonusScore = angle < 0 ? 10 : 0;

    const totalScore = score + bonusScore;

    if (totalScore > bestScore) {
      bestScore = totalScore;
      bestPosition = { x: candidateX, y: candidateY, angle };
    }
  }

  return bestPosition;
}

/**
 * Calculate intelligent anchor point on label edge for leader lines
 * Connects to the side of label closest to the node for clean diagonal lines
 *
 * @param label - Label node with position and dimensions
 * @returns Anchor point {x, y}
 */
export function calculateLabelAnchor(label: LabelNode): { x: number; y: number } {
  const labelX = label.x || 0;
  const labelY = label.y || 0;
  const dx = labelX - label.nodeX;
  const dy = labelY - label.nodeY;

  let anchorX = labelX;
  let anchorY = labelY;

  // Determine which edge to anchor to based on label position relative to node
  if (dy < 0) {
    // Label above node - anchor to bottom edge
    anchorY = labelY + label.height / 2;
  } else {
    // Label below node - anchor to top edge
    anchorY = labelY - label.height / 2;
  }

  // For horizontal positioning, only adjust if significantly offset
  if (Math.abs(dx) > label.width / 4) {
    if (dx > 0) {
      // Label right of node - anchor to left edge
      anchorX = labelX - label.width / 2 + 5;
    } else {
      // Label left of node - anchor to right edge
      anchorX = labelX + label.width / 2 - 5;
    }
  }

  return { x: anchorX, y: anchorY };
}
