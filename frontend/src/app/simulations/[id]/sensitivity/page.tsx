'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { clsx } from 'clsx';
import { ChevronLeft, BarChart3, Download, Info } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import dynamic from 'next/dynamic';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type {
  SensitivityParameter as ApiSensitivityParameter,
  TornadoChartData as ApiTornadoChartData,
  SensitivityParameterLegacy,
  TornadoChartDataLegacy,
} from '@/lib/types';

const TornadoChart = dynamic(
  () => import('@/components/visualization/TornadoChart').then(mod => ({ default: mod.TornadoChart })),
  { ssr: false, loading: () => <div className="h-[500px] animate-pulse bg-zinc-800/50 rounded-lg" /> }
);

const backToSimulationLinkClass = clsx(
  'inline-flex items-center justify-center gap-2 font-medium rounded-lg border transition-all duration-200',
  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:ring-offset-2 focus:ring-offset-background',
  'bg-transparent hover:bg-background-tertiary text-foreground-muted border-transparent',
  'px-3 py-1.5 text-sm'
);

// Convert API response to chart format
function convertApiDataToChart(
  apiData: ApiTornadoChartData
): TornadoChartDataLegacy {
  const parameters: SensitivityParameterLegacy[] = apiData.parameters.map(
    (p: ApiSensitivityParameter, index: number) => ({
      id: `param-${index}`,
      name: p.name,
      description: p.description,
      baseValue: p.base_value,
      lowValue: p.low_value,
      highValue: p.high_value,
      impact: Math.abs(p.impact_score),
      impactDirection:
        p.high_outcome > p.low_outcome ? 'positive' : 'negative',
      unit: '',
    })
  );

  const baselineValue =
    apiData.baseline_outcome?.policy_adoption_rate ||
    apiData.baseline_outcome?.time_to_consensus ||
    50;

  return {
    parameters,
    outcomeMetric: apiData.outcome_metrics?.[0] || 'Outcome',
    outcomeUnit: '',
    baselineValue,
  };
}

const outcomeMetrics = [
  { id: 'npv', name: 'Net Present Value (NPV)', unit: 'M$' },
  { id: 'roi', name: 'Return on Investment (ROI)', unit: '%' },
  { id: 'payback', name: 'Payback Period', unit: 'years' },
  { id: 'irr', name: 'Internal Rate of Return', unit: '%' },
];

const LOAD_FALLBACK = 'Failed to load sensitivity analysis.';

function sensitivityLoadErrorMessage(error: unknown): string {
  if (error == null) return LOAD_FALLBACK;

  const msg = error instanceof Error ? error.message : String(error);
  const lower = msg.toLowerCase();

  const isNetworkFailure =
    (typeof DOMException !== 'undefined' &&
      error instanceof DOMException &&
      error.name === 'NetworkError') ||
    error instanceof TypeError ||
    lower.includes('failed to fetch') ||
    lower.includes('networkerror') ||
    lower.includes('load failed') ||
    lower.includes('net::err_') ||
    lower.includes('err_network_changed');

  if (isNetworkFailure) {
    return 'Network error: failed to connect';
  }

  const httpInText = msg.match(/\bHTTP\s+(\d{3})\b/i);
  const parenThreeDigits = msg.match(/\((\d{3})\)/);
  const status = httpInText?.[1] ?? parenThreeDigits?.[1];

  if (status !== undefined) {
    return `API error ${status}: ${msg}`;
  }

  if (msg.trim().length > 0) {
    return `API error: ${msg}`;
  }

  return LOAD_FALLBACK;
}

export default function SensitivityPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<TornadoChartDataLegacy | null>(null);
  const [selectedMetric, setSelectedMetric] = useState('npv');
  const [selectedParam, setSelectedParam] = useState<SensitivityParameterLegacy | null>(null);
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const [chartWidth, setChartWidth] = useState(900);

  useEffect(() => {
    const el = chartContainerRef.current;
    if (!el) return;

    const updateSize = () => {
      const next = Math.max(760, Math.floor(el.clientWidth));
      setChartWidth(next);
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const loadSimulation = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const simulationData = await api.getSimulation(simulationId);

      if (simulationData === null) {
        setCurrentSimulation(null);
        setChartData(null);
      } else {
        setCurrentSimulation(simulationData);

        const sensitivityData = await api.getSensitivityAnalysis(simulationId);
        if (sensitivityData) {
          setChartData(convertApiDataToChart(sensitivityData));
        } else {
          setChartData(null);
        }
      }
    } catch (error) {
      setCurrentSimulation(null);
      setChartData(null);
      setLoadError(sensitivityLoadErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, [simulationId, setCurrentSimulation]);

  useEffect(() => {
    void loadSimulation();
  }, [loadSimulation]);

  const handleExportData = () => {
    if (!chartData) return;
    
    const data = {
      simulation: currentSimulation?.name,
      outcomeMetric: chartData.outcomeMetric,
      baselineValue: chartData.baselineValue,
      parameters: chartData.parameters,
      exportedAt: new Date().toISOString(),
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `sensitivity-analysis-${simulationId}.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  const selectedMetricInfo = outcomeMetrics.find((m) => m.id === selectedMetric);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading sensitivity analysis...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 px-4 text-center">
        <div className="text-red-400 max-w-md">{loadError}</div>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => void loadSimulation()}
        >
          Retry
        </Button>
        <Link
          href={`/simulations/${simulationId}`}
          className={backToSimulationLinkClass}
        >
          <ChevronLeft className="w-4 h-4 shrink-0" aria-hidden />
          Back to simulation
        </Link>
      </div>
    );
  }

  if (!currentSimulation) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Simulation not found</div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center justify-center p-8 text-center max-w-md">
          <BarChart3 className="w-12 h-12 text-slate-500 mb-4" />
          <h2 className="text-xl font-bold text-slate-200">Insufficient Data</h2>
          <p className="text-slate-400 mt-2">
            Sensitivity analysis requires sufficient simulation rounds to be completed in order to measure parameter variance.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <Link href={`/simulations/${simulationId}`} className={backToSimulationLinkClass}>
              <ChevronLeft className="w-4 h-4 shrink-0" aria-hidden />
              Back
            </Link>
            <div className="min-w-0">
              <h1 className="text-lg md:text-xl font-bold text-slate-100 truncate">
                Sensitivity Analysis
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                {currentSimulation.name}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Metric Selector */}
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50"
            >
              {outcomeMetrics.map((metric) => (
                <option key={metric.id} value={metric.id}>
                  {metric.name}
                </option>
              ))}
            </select>
            
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Download className="w-4 h-4" />}
              onClick={handleExportData}
            >
              Export Data
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-6xl mx-auto space-y-4 md:space-y-6">
          {/* Chart Card */}
          <Card>
            <div className="p-4 md:p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 md:mb-6 gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    Tornado Chart
                  </h2>
                  <p className="text-sm text-slate-400 mt-1">
                    Impact of parameter variations on {selectedMetricInfo?.name}
                  </p>
                </div>
                <div className="text-left sm:text-right">
                  <div className="text-sm text-slate-400">Baseline Value</div>
                  <div className="text-xl md:text-2xl font-bold text-slate-200">
                    {chartData.baselineValue.toFixed(1)} {selectedMetricInfo?.unit}
                  </div>
                </div>
              </div>

              <div ref={chartContainerRef} className="overflow-x-auto">
                <div style={{ minWidth: `${chartWidth}px` }}>
                  <TornadoChart
                    data={chartData}
                    width={chartWidth}
                    height={500}
                    onParameterClick={setSelectedParam}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* Parameter Details Table */}
          <Card>
            <div className="p-4 md:p-6">
              <h2 className="text-lg font-semibold text-slate-200 mb-4">
                Parameter Details
              </h2>
              
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                        Parameter
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                        Description
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">
                        Base Value
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">
                        Low (-)
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">
                        High (+)
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">
                        Impact
                      </th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-slate-400">
                        Direction
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.parameters
                      .sort((a, b) => b.impact - a.impact)
                      .map((param) => (
                        <tr
                          key={param.id}
                          className={`
                            border-b border-slate-700/50 last:border-0
                            hover:bg-slate-700/30 transition-colors cursor-pointer
                            ${selectedParam?.id === param.id ? 'bg-slate-700/50' : ''}
                          `}
                          onClick={() => setSelectedParam(param)}
                        >
                          <td className="py-3 px-4">
                            <div className="font-medium text-slate-200">{param.name}</div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="text-sm text-slate-400">{param.description}</div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="text-slate-300">
                              {param.baseValue.toFixed(1)} {param.unit}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="text-red-400">
                              {param.lowValue.toFixed(1)} {param.unit}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="text-teal-400">
                              {param.highValue.toFixed(1)} {param.unit}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="font-medium text-slate-200">
                              {param.impact.toFixed(2)}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`
                                inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                                ${param.impactDirection === 'positive'
                                  ? 'bg-teal-500/20 text-teal-400'
                                  : 'bg-red-500/20 text-red-400'
                                }
                              `}
                            >
                              {param.impactDirection === 'positive' ? 'Positive' : 'Negative'}
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>

          {/* Interpretation Guide */}
          <Card>
            <div className="p-4 md:p-6">
              <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Info className="w-5 h-5 text-accent" />
                Interpretation Guide
              </h2>
              
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 md:gap-6 text-sm text-slate-300">
                <div>
                  <h3 className="font-medium text-slate-200 mb-2">Reading the Chart</h3>
                  <ul className="list-disc pl-5 space-y-2 text-slate-400 marker:text-accent">
                    <li>Bars extending right show upside when the parameter increases.</li>
                    <li>Bars extending left show downside when the parameter decreases.</li>
                    <li>Longer bars indicate higher sensitivity and more scenario leverage.</li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-medium text-slate-200 mb-2">Key Insights</h3>
                  <ul className="list-disc pl-5 space-y-2 text-slate-400 marker:text-accent">
                    <li>Prioritize risk controls around the longest bars first.</li>
                    <li>Top-ranked parameters contribute the most outcome volatility.</li>
                    <li>Use the highest-impact parameters as the core of scenario planning.</li>
                  </ul>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
