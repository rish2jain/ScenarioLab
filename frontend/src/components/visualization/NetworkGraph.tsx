'use client';

import React, { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { clsx } from 'clsx';
import type { NetworkNode, NetworkEdge, NetworkGraphData } from '@/lib/types';

/** Cheap pass on the render path; full refinement runs in idle time. */
const INITIAL_FORCE_ITERATIONS = 24;
const REFINE_FORCE_ITERATIONS = 126;
const MAX_LAYOUT_CACHE_ENTRIES = 32;

type LayoutPositions = Record<string, { x: number; y: number }>;

const layoutCache = new Map<string, LayoutPositions>();

/** Read from cache and move key to most-recent end (Map insertion order = LRU). */
function readLayoutCache(key: string): LayoutPositions | undefined {
  const v = layoutCache.get(key);
  if (v === undefined) return undefined;
  layoutCache.delete(key);
  layoutCache.set(key, v);
  return v;
}

/** Insert or update; existing keys move to most-recent end. */
function writeLayoutCache(key: string, positions: LayoutPositions): void {
  layoutCache.delete(key);
  layoutCache.set(key, positions);
}

/**
 * Drop least-recently-used entries. After readLayoutCache/writeLayoutCache, iteration order
 * is LRU: oldest at keys().next(), newest at the end.
 */
function pruneLayoutCache(): void {
  while (layoutCache.size > MAX_LAYOUT_CACHE_ENTRIES) {
    const lru = layoutCache.keys().next().value;
    if (lru === undefined) break;
    layoutCache.delete(lru);
  }
}

/** Stable key from topology + canvas size so layouts reuse across re-renders. */
function buildLayoutCacheKey(
  data: { nodes: NetworkNode[]; edges: NetworkEdge[] },
  width: number,
  height: number
): string {
  const nodeIds = [...data.nodes].map((n) => n.id).sort().join('\x00');
  const edgeKeys = [...data.edges]
    .map((e) => `${e.source}\x00${e.target}\x00${e.id}`)
    .sort()
    .join('\x01');
  return `${width}x${height}\n${nodeIds}\n${edgeKeys}`;
}

function hashStringToUint32(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Deterministic PRNG in [0, 1) for initial placement (replaces Math.random). */
function mulberry32(seed: number): () => number {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function extractPositions(nodes: NetworkNode[]): LayoutPositions {
  const out: LayoutPositions = {};
  for (const n of nodes) {
    out[n.id] = { x: n.x ?? 0, y: n.y ?? 0 };
  }
  return out;
}

function applyCachedPositions(
  nodes: NetworkNode[],
  positions: LayoutPositions
): NetworkNode[] {
  return nodes.map((n) => {
    const p = positions[n.id];
    if (!p) return { ...n };
    return { ...n, x: p.x, y: p.y, vx: 0, vy: 0 };
  });
}

function scheduleIdleTask(fn: () => void): { id: number; usedIdleCallback: boolean } {
  if (typeof requestIdleCallback !== 'undefined') {
    const id = requestIdleCallback(() => fn(), { timeout: 2500 });
    return { id, usedIdleCallback: true };
  }
  const id = window.setTimeout(fn, 0) as unknown as number;
  return { id, usedIdleCallback: false };
}

function cancelIdleTask(id: number, usedIdleCallback: boolean): void {
  if (usedIdleCallback && typeof cancelIdleCallback !== 'undefined') {
    cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}

interface NetworkGraphProps {
  data: NetworkGraphData;
  width?: number;
  height?: number;
  onNodeClick?: (node: NetworkNode) => void;
  selectedNodeId?: string | null;
  filterRoles?: string[];
  filterCoalitions?: string[];
  sentimentThreshold?: number;
  className?: string;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  content: React.ReactNode;
}

interface RunForceSimulationOptions {
  iterations?: number;
  /** Seed for deterministic initial placement when x/y are zero (mulberry32). */
  seed?: number;
}

// Force-directed layout simulation (mutates node x/y/vx/vy in-place; does not reorder caller's array)
function runForceSimulation(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  width: number,
  height: number,
  options: RunForceSimulationOptions = {}
): NetworkNode[] {
  const iterations = options.iterations ?? 100;
  const seed = options.seed;

  if (nodes.length === 0) {
    return nodes;
  }

  const sortedNodes = [...nodes].sort((a, b) => a.id.localeCompare(b.id));

  const centerX = width / 2;
  const centerY = height / 2;
  const k = Math.sqrt((width * height) / sortedNodes.length) * 0.5; // optimal distance

  const rand = mulberry32(seed ?? 0x9e3779b9);

  // Ensure velocity is initialized (do not coerce missing x/y to 0 — that breaks
  // the “uninitialized position” check below for legitimate (0, 0) placements).
  for (const node of sortedNodes) {
    node.vx = node.vx ?? 0;
    node.vy = node.vy ?? 0;
  }

  // Initialize positions when coordinates are missing (deterministic when seed is given)
  sortedNodes.forEach((node) => {
    if (node.x == null || node.y == null) {
      node.x = centerX + (rand() - 0.5) * 200;
      node.y = centerY + (rand() - 0.5) * 200;
    }
  });

  const nodeById = new Map(sortedNodes.map((n) => [n.id, n]));

  for (let i = 0; i < iterations; i++) {
    // Repulsion (Coulomb's law) - nodes repel each other
    for (let a = 0; a < sortedNodes.length; a++) {
      for (let b = a + 1; b < sortedNodes.length; b++) {
        const nodeA = sortedNodes[a];
        const nodeB = sortedNodes[b];
        const dx = (nodeB.x ?? 0) - (nodeA.x ?? 0);
        const dy = (nodeB.y ?? 0) - (nodeA.y ?? 0);
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (k * k) / dist;
        const fx = (dx / dist) * force * 0.05;
        const fy = (dy / dist) * force * 0.05;

        nodeA.vx = (nodeA.vx ?? 0) - fx;
        nodeA.vy = (nodeA.vy ?? 0) - fy;
        nodeB.vx = (nodeB.vx ?? 0) + fx;
        nodeB.vy = (nodeB.vy ?? 0) + fy;
      }
    }

    // Attraction (spring force) - edges pull nodes together
    edges.forEach((edge) => {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (source && target) {
        const dx = (target.x ?? 0) - (source.x ?? 0);
        const dy = (target.y ?? 0) - (source.y ?? 0);
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = ((dist * dist) / k) * 0.01;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        source.vx = (source.vx ?? 0) + fx;
        source.vy = (source.vy ?? 0) + fy;
        target.vx = (target.vx ?? 0) - fx;
        target.vy = (target.vy ?? 0) - fy;
      }
    });

    // Center gravity - pull toward center
    sortedNodes.forEach((node) => {
      const dx = centerX - (node.x ?? 0);
      const dy = centerY - (node.y ?? 0);
      node.vx = (node.vx ?? 0) + dx * 0.001;
      node.vy = (node.vy ?? 0) + dy * 0.001;
    });

    // Apply velocity with damping
    sortedNodes.forEach((node) => {
      node.vx = (node.vx ?? 0) * 0.9; // damping
      node.vy = (node.vy ?? 0) * 0.9;
      node.x = (node.x ?? 0) + (node.vx ?? 0);
      node.y = (node.y ?? 0) + (node.vy ?? 0);

      // Keep within bounds with padding
      const padding = 50;
      node.x = Math.max(padding, Math.min(width - padding, node.x ?? 0));
      node.y = Math.max(padding, Math.min(height - padding, node.y ?? 0));
    });
  }

  return sortedNodes;
}

export function NetworkGraph({
  data,
  width = 800,
  height = 600,
  onNodeClick,
  selectedNodeId,
  filterRoles = [],
  filterCoalitions = [],
  sentimentThreshold = -1,
  className,
}: NetworkGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    content: null,
  });

  // Filter data based on props
  const filteredData = useMemo(() => {
    let filteredNodes = [...data.nodes];
    let filteredEdges = [...data.edges];

    // Filter by roles
    if (filterRoles.length > 0) {
      filteredNodes = filteredNodes.filter((n) => filterRoles.includes(n.role));
      const nodeIds = new Set(filteredNodes.map((n) => n.id));
      filteredEdges = filteredEdges.filter(
        (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
      );
    }

    // Filter by coalitions
    if (filterCoalitions.length > 0) {
      filteredNodes = filteredNodes.filter(
        (n) => n.coalition && filterCoalitions.includes(n.coalition)
      );
      const nodeIds = new Set(filteredNodes.map((n) => n.id));
      filteredEdges = filteredEdges.filter(
        (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
      );
    }

    // Filter edges by sentiment threshold
    filteredEdges = filteredEdges.filter(
      (e) => Math.abs(e.sentimentScore) >= sentimentThreshold
    );

    return { nodes: filteredNodes, edges: filteredEdges };
  }, [data, filterRoles, filterCoalitions, sentimentThreshold]);

  const layoutKey = useMemo(
    () => buildLayoutCacheKey(filteredData, width, height),
    [filteredData, width, height]
  );

  /** Positions from the last idle refinement; keyed so a layout change does not need a reset effect. */
  const [idleRefined, setIdleRefined] = useState<{
    key: string;
    positions: LayoutPositions;
  } | null>(null);

  const cheapLayout = useMemo(() => {
    const fromIdle =
      idleRefined?.key === layoutKey ? idleRefined.positions : null;
    const cached = readLayoutCache(layoutKey) ?? fromIdle;
    if (cached) {
      return applyCachedPositions(filteredData.nodes, cached);
    }
    const seed = hashStringToUint32(layoutKey);
    return runForceSimulation(
      filteredData.nodes.map((n) => ({ ...n })),
      filteredData.edges,
      width,
      height,
      { iterations: INITIAL_FORCE_ITERATIONS, seed }
    );
  }, [
    layoutKey,
    filteredData.nodes,
    filteredData.edges,
    width,
    height,
    idleRefined,
  ]);

  useEffect(() => {
    if (layoutCache.has(layoutKey)) {
      return;
    }
    if (cheapLayout.length === 0) {
      return;
    }

    const copy = cheapLayout.map((n) => ({ ...n }));
    const edges = filteredData.edges;

    const { id: idleId, usedIdleCallback } = scheduleIdleTask(() => {
      const refineSeed = hashStringToUint32(`${layoutKey}|refine`);
      const refined = runForceSimulation(copy, edges, width, height, {
        iterations: REFINE_FORCE_ITERATIONS,
        seed: refineSeed,
      });
      const positions = extractPositions(refined);
      writeLayoutCache(layoutKey, positions);
      pruneLayoutCache();
      setIdleRefined({ key: layoutKey, positions });
    });

    return () => cancelIdleTask(idleId, usedIdleCallback);
  }, [layoutKey, cheapLayout, filteredData.edges, width, height]);

  const nodes = cheapLayout;

  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes]
  );

  // Get edge color based on sentiment
  const getEdgeColor = (sentiment: NetworkEdge['sentiment']) => {
    switch (sentiment) {
      case 'positive':
        return '#22c55e';
      case 'negative':
        return '#ef4444';
      default:
        return '#64748b';
    }
  };

  // Get node radius based on authority level
  const getNodeRadius = (authorityLevel: number) => {
    return 8 + authorityLevel * 2;
  };

  // Handle zoom with mouse wheel
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom((prev) => Math.max(0.5, Math.min(3, prev * delta)));
    },
    []
  );

  // Handle pan
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === svgRef.current) {
        setIsDragging(true);
        setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      }
    },
    [pan]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        setPan({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
      }
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Handle edge hover
  const handleEdgeMouseEnter = (
    e: React.MouseEvent,
    edge: NetworkEdge,
    sourceNode: NetworkNode,
    targetNode: NetworkNode
  ) => {
    setTooltip({
      visible: true,
      x: e.clientX + 10,
      y: e.clientY - 10,
      content: (
        <div className="space-y-1">
          <div className="font-medium text-slate-200">
            {sourceNode.name} ↔ {targetNode.name}
          </div>
          <div className="text-sm text-slate-400">
            Sentiment:{' '}
            <span
              style={{
                color: getEdgeColor(edge.sentiment),
              }}
            >
              {edge.sentimentScore > 0 ? '+' : ''}
              {edge.sentimentScore.toFixed(2)}
            </span>
          </div>
          <div className="text-sm text-slate-400">
            Messages: {edge.messageCount}
          </div>
        </div>
      ),
    });
  };

  const handleEdgeMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  // Handle node hover
  const handleNodeMouseEnter = useCallback(
    (e: React.MouseEvent, node: NetworkNode) => {
      setTooltip({
        visible: true,
        x: e.clientX + 10,
        y: e.clientY - 10,
        content: (
          <div className="space-y-1">
            <div className="font-medium text-slate-200">{node.name}</div>
            <div className="text-sm text-slate-400 capitalize">
              {node.role} • {node.archetype}
            </div>
            <div className="text-xs text-slate-500">
              Click to view full details
            </div>
          </div>
        ),
      });
    },
    []
  );

  const handleNodeMouseLeave = useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  // Export functions
  const exportAsPNG = useCallback(() => {
    if (!svgRef.current) return;
    
    const svg = svgRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Fill background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    // Convert SVG to image
    const svgData = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      const link = document.createElement('a');
      link.download = `network-graph-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
  }, [width, height]);

  const exportAsSVG = useCallback(() => {
    if (!svgRef.current) return;
    
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `network-graph-${Date.now()}.svg`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div className={clsx('relative', className)}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="cursor-move"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <defs>
          {/* Arrow marker for directed edges */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
          </marker>
        </defs>
        
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Edges */}
          {filteredData.edges.map((edge) => {
            const source = nodeMap.get(edge.source);
            const target = nodeMap.get(edge.target);
            if (!source || !target) return null;

            return (
              <line
                key={edge.id}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={getEdgeColor(edge.sentiment)}
                strokeWidth={Math.max(1, (edge.messageCount || 1) * 0.5)}
                strokeOpacity={0.7}
                className="transition-all duration-200"
                onMouseEnter={(e) =>
                  handleEdgeMouseEnter(e, edge, source, target)
                }
                onMouseLeave={handleEdgeMouseLeave}
                style={{ cursor: 'pointer' }}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const radius = getNodeRadius(node.authorityLevel);
            const isSelected = selectedNodeId === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                className="cursor-pointer"
                onClick={() => onNodeClick?.(node)}
                onMouseEnter={(e) => handleNodeMouseEnter(e, node)}
                onMouseLeave={handleNodeMouseLeave}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    r={radius + 4}
                    fill="none"
                    stroke="#14b8a6"
                    strokeWidth={2}
                    strokeDasharray="4 2"
                  />
                )}
                
                {/* Node circle */}
                <circle
                  r={radius}
                  fill={node.color}
                  stroke="#1e293b"
                  strokeWidth={2}
                  className="transition-all duration-200 hover:opacity-80"
                />
                
                {/* Node label */}
                <text
                  y={radius + 15}
                  textAnchor="middle"
                  fill="#e2e8f0"
                  fontSize={11}
                  fontWeight={500}
                >
                  {node.name}
                </text>
                
                {/* Role label */}
                <text
                  y={radius + 28}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize={9}
                >
                  {node.role}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Controls */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-2">
        <button
          onClick={() => setZoom((prev) => Math.min(3, prev * 1.2))}
          className="w-8 h-8 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-center text-slate-300 hover:bg-slate-700 transition-colors"
        >
          +
        </button>
        <button
          onClick={() => setZoom((prev) => Math.max(0.5, prev / 1.2))}
          className="w-8 h-8 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-center text-slate-300 hover:bg-slate-700 transition-colors"
        >
          −
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="w-8 h-8 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-center text-slate-300 hover:bg-slate-700 transition-colors text-xs"
        >
          ⌂
        </button>
      </div>

      {/* Export buttons */}
      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={exportAsPNG}
          className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Export PNG
        </button>
        <button
          onClick={exportAsSVG}
          className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Export SVG
        </button>
      </div>

      {/* Zoom level indicator */}
      <div className="absolute bottom-4 right-4 px-2 py-1 bg-slate-800/80 border border-slate-700 rounded text-xs text-slate-400">
        {Math.round(zoom * 100)}%
      </div>

      {/* Tooltip */}
      {tooltip.visible && (
        <div
          className="fixed z-50 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.content}
        </div>
      )}
    </div>
  );
}

export default NetworkGraph;
