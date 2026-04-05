'use client';

import React, { useState, useMemo, useRef, useCallback } from 'react';
import { clsx } from 'clsx';
import type { SensitivityParameterLegacy, TornadoChartDataLegacy } from '@/lib/types';

interface TornadoChartProps {
  data: TornadoChartDataLegacy;
  width?: number;
  height?: number;
  className?: string;
  onParameterClick?: (param: SensitivityParameterLegacy) => void;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  content: React.ReactNode;
}

export function TornadoChart({
  data,
  width = 800,
  height = 500,
  className,
  onParameterClick,
}: TornadoChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    content: null,
  });

  // Sort parameters by impact magnitude (largest at top)
  const sortedParams = useMemo(() => {
    return [...data.parameters].sort((a, b) => b.impact - a.impact);
  }, [data.parameters]);

  // Chart dimensions — right margin must leave room for per-row impact labels and the
  // legend group (origin at width - margin.right + 12); space to SVG edge = margin.right - 12.
  const LEGEND_CONTENT_WIDTH = 132;
  const margin = {
    top: 72,
    right: 12 + LEGEND_CONTENT_WIDTH + 8,
    bottom: 56,
    left: 220,
  };
  const chartWidth = width - margin.left - margin.right;
  // Dynamic height to prevent Y-axis labels from overlapping if there are many parameters
  const minBarHeight = 24;
  const barGap = 8;
  const dynamicHeight = Math.max(
    height,
    sortedParams.length * (minBarHeight + barGap) + margin.top + margin.bottom
  );
  
  const chartHeight = dynamicHeight - margin.top - margin.bottom;

  // Calculate scales (memoized so tooltip / other state do not rebuild the map)
  const paramExtents = useMemo(
    () =>
      sortedParams.map((param) => ({
        param,
        leftDelta: Math.max(0, Math.abs(param.baseValue - param.lowValue)),
        rightDelta: Math.max(0, Math.abs(param.highValue - param.baseValue)),
      })),
    [sortedParams]
  );
  const paramExtentsMap = useMemo(
    () =>
      new Map(
        paramExtents.map((entry) => [
          entry.param.id,
          { leftDelta: entry.leftDelta, rightDelta: entry.rightDelta },
        ])
      ),
    [paramExtents]
  );
  const maxDelta = Math.max(
    1,
    ...paramExtents.flatMap(({ leftDelta, rightDelta }) => [leftDelta, rightDelta])
  );
  const scaleFactor = (chartWidth / 2) / maxDelta;

  const barHeight = sortedParams.length === 0 ? 0 : Math.min(40, (chartHeight - (sortedParams.length - 1) * barGap) / sortedParams.length);

  // Center line X position
  const centerX = margin.left + chartWidth / 2;

  const handleBarHover = useCallback(
    (e: React.MouseEvent, param: SensitivityParameterLegacy) => {
      const lowChange = ((param.lowValue - param.baseValue) / param.baseValue) * 100;
      const highChange = ((param.highValue - param.baseValue) / param.baseValue) * 100;

      setTooltip({
        visible: true,
        x: e.clientX + 10,
        y: e.clientY - 10,
        content: (
          <div className="space-y-2 min-w-[200px]">
            <div className="font-semibold text-slate-200">{param.name}</div>
            <div className="text-sm text-slate-400">{param.description}</div>
            <div className="pt-2 border-t border-slate-700 space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Base Value:</span>
                <span className="text-slate-300">
                  {param.baseValue.toFixed(2)} {param.unit || ''}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-red-400">Low (-):</span>
                <span className="text-slate-300">
                  {param.lowValue.toFixed(2)} {param.unit || ''}
                  <span className="text-red-400 ml-1">({lowChange > 0 ? '+' : ''}{lowChange.toFixed(1)}%)</span>
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-teal-400">High (+):</span>
                <span className="text-slate-300">
                  {param.highValue.toFixed(2)} {param.unit || ''}
                  <span className="text-teal-400 ml-1">({highChange > 0 ? '+' : ''}{highChange.toFixed(1)}%)</span>
                </span>
              </div>
              <div className="flex justify-between text-sm pt-1 border-t border-slate-700">
                <span className="text-slate-500">Impact:</span>
                <span className={param.impactDirection === 'positive' ? 'text-teal-400' : 'text-red-400'}>
                  {param.impact.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        ),
      });
    },
    []
  );

  const handleBarLeave = useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  // Export functions
  const exportAsPNG = useCallback(() => {
    if (!svgRef.current) return;

    const svg = svgRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = dynamicHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Fill background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, dynamicHeight);

    // Convert SVG to image
    const svgData = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      const link = document.createElement('a');
      link.download = `tornado-chart-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    const svgBase64 = btoa(
      unescape(encodeURIComponent(svgData))
    );
    img.src = 'data:image/svg+xml;base64,' + svgBase64;
  }, [width, dynamicHeight]);

  const exportAsSVG = useCallback(() => {
    if (!svgRef.current) return;

    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `tornado-chart-${Date.now()}.svg`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div className={clsx('relative', className)}>
      <svg
        ref={svgRef}
        width={width}
        height={dynamicHeight}
        className="overflow-visible"
      >
        {/* Background */}
        <rect
          x={margin.left}
          y={margin.top}
          width={chartWidth}
          height={chartHeight}
          fill="rgba(30, 41, 59, 0.3)"
          rx={8}
        />

        {/* Title */}
        <text
          x={width / 2}
          y={30}
          textAnchor="middle"
          fill="#f1f5f9"
          fontSize={16}
          fontWeight={600}
        >
          Sensitivity Analysis: {data.outcomeMetric}
        </text>
        <text
          x={width / 2}
          y={50}
          textAnchor="middle"
          fill="#94a3b8"
          fontSize={12}
        >
          Baseline: {data.baselineValue.toFixed(2)} {data.outcomeUnit || ''}
        </text>

        {/* Center line */}
        <line
          x1={centerX}
          y1={margin.top}
          x2={centerX}
          y2={margin.top + chartHeight}
          stroke="#475569"
          strokeWidth={2}
          strokeDasharray="4 4"
        />

        {/* Y-axis labels and bars */}
        {sortedParams.map((param, index) => {
          const y = margin.top + index * (barHeight + barGap);
          const { leftDelta, rightDelta } = paramExtentsMap.get(param.id) ?? {
            leftDelta: 0,
            rightDelta: 0,
          };
          const leftBarWidth = leftDelta * scaleFactor;
          const rightBarWidth = rightDelta * scaleFactor;

          return (
            <g key={param.id}>
              {/* Parameter label */}
              <text
                x={margin.left - 10}
                y={y + barHeight / 2}
                textAnchor="end"
                dominantBaseline="middle"
                fill="#e2e8f0"
                fontSize={12}
                fontWeight={500}
              >
                {param.name}
              </text>

              {/* Left bar (decrease/negative impact) */}
              <rect
                x={centerX - leftBarWidth}
                y={y}
                width={leftBarWidth}
                height={barHeight}
                fill="#ef4444"
                rx={4}
                className="cursor-pointer transition-opacity hover:opacity-80"
                onMouseEnter={(e) => handleBarHover(e, param)}
                onMouseLeave={handleBarLeave}
                onClick={() => onParameterClick?.(param)}
              />

              {/* Right bar (increase/positive impact) */}
              <rect
                x={centerX}
                y={y}
                width={rightBarWidth}
                height={barHeight}
                fill="#14b8a6"
                rx={4}
                className="cursor-pointer transition-opacity hover:opacity-80"
                onMouseEnter={(e) => handleBarHover(e, param)}
                onMouseLeave={handleBarLeave}
                onClick={() => onParameterClick?.(param)}
              />

              {/* Impact value label */}
              <text
                x={width - margin.right + 12}
                y={y + barHeight / 2}
                dominantBaseline="middle"
                fill="#94a3b8"
                fontSize={11}
                textAnchor="end"
              >
                {param.impact.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        <text
          x={centerX - chartWidth / 4}
          y={dynamicHeight - 20}
          textAnchor="middle"
          fill="#64748b"
          fontSize={11}
        >
          Decrease
        </text>
        <text
          x={centerX + chartWidth / 4}
          y={dynamicHeight - 20}
          textAnchor="middle"
          fill="#64748b"
          fontSize={11}
        >
          Increase
        </text>
        <text
          x={centerX}
          y={dynamicHeight - 20}
          textAnchor="middle"
          fill="#94a3b8"
          fontSize={11}
          fontWeight={500}
        >
          Baseline
        </text>

        {/* Legend */}
        <g transform={`translate(${width - margin.right + 12}, ${margin.top})`}>
          <rect
            x={0}
            y={0}
            width={10}
            height={10}
            fill="#14b8a6"
            rx={2}
          />
          <text
            x={16}
            y={9}
            fill="#94a3b8"
            fontSize={11}
          >
            Positive Impact
          </text>
          <rect
            x={0}
            y={20}
            width={10}
            height={10}
            fill="#ef4444"
            rx={2}
          />
          <text
            x={16}
            y={29}
            fill="#94a3b8"
            fontSize={11}
          >
            Negative Impact
          </text>
        </g>
      </svg>

      {/* Export buttons */}
      <div className="absolute top-0 right-0 flex gap-2">
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

export default TornadoChart;
