'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, BarChart3, Download, Info } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { TornadoChart } from '@/components/visualization/TornadoChart';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type {
  Simulation,
  SensitivityParameter as ApiSensitivityParameter,
  TornadoChartData as ApiTornadoChartData,
  SensitivityParameterLegacy,
  TornadoChartDataLegacy,
} from '@/lib/types';

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

// Mock data generator (fallback)
function generateMockSensitivityData(): TornadoChartDataLegacy {
  const parameters: SensitivityParameterLegacy[] = [
    {
      id: 'param-1',
      name: 'Market Growth Rate',
      description: 'Annual growth rate of the target market',
      baseValue: 5.0,
      lowValue: 2.5,
      highValue: 8.5,
      impact: 15.2,
      impactDirection: 'positive',
      unit: '%',
    },
    {
      id: 'param-2',
      name: 'Integration Cost',
      description: 'Total cost of merging operations and systems',
      baseValue: 50.0,
      lowValue: 35.0,
      highValue: 75.0,
      impact: 12.8,
      impactDirection: 'negative',
      unit: 'M$',
    },
    {
      id: 'param-3',
      name: 'Synergy Realization',
      description: 'Percentage of projected synergies achieved',
      baseValue: 70.0,
      lowValue: 40.0,
      highValue: 95.0,
      impact: 18.5,
      impactDirection: 'positive',
      unit: '%',
    },
    {
      id: 'param-4',
      name: 'Employee Retention',
      description: 'Percentage of key employees retained post-merger',
      baseValue: 85.0,
      lowValue: 60.0,
      highValue: 95.0,
      impact: 10.3,
      impactDirection: 'positive',
      unit: '%',
    },
    {
      id: 'param-5',
      name: 'Customer Churn',
      description: 'Percentage of customers lost during transition',
      baseValue: 8.0,
      lowValue: 3.0,
      highValue: 15.0,
      impact: 14.7,
      impactDirection: 'negative',
      unit: '%',
    },
    {
      id: 'param-6',
      name: 'Regulatory Delay',
      description: 'Additional months for regulatory approval',
      baseValue: 3.0,
      lowValue: 0.0,
      highValue: 9.0,
      impact: 8.9,
      impactDirection: 'negative',
      unit: 'months',
    },
    {
      id: 'param-7',
      name: 'Technology Integration',
      description: 'Success rate of systems integration',
      baseValue: 75.0,
      lowValue: 50.0,
      highValue: 95.0,
      impact: 11.4,
      impactDirection: 'positive',
      unit: '%',
    },
    {
      id: 'param-8',
      name: 'Cultural Alignment',
      description: 'Degree of cultural compatibility between organizations',
      baseValue: 65.0,
      lowValue: 30.0,
      highValue: 90.0,
      impact: 9.6,
      impactDirection: 'positive',
      unit: '%',
    },
  ];

  return {
    parameters,
    outcomeMetric: 'Net Present Value (NPV)',
    outcomeUnit: 'M$',
    baselineValue: 125.5,
  };
}

const outcomeMetrics = [
  { id: 'npv', name: 'Net Present Value (NPV)', unit: 'M$' },
  { id: 'roi', name: 'Return on Investment (ROI)', unit: '%' },
  { id: 'payback', name: 'Payback Period', unit: 'years' },
  { id: 'irr', name: 'Internal Rate of Return', unit: '%' },
];

export default function SensitivityPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [chartData, setChartData] = useState<TornadoChartDataLegacy | null>(null);
  const [selectedMetric, setSelectedMetric] = useState('npv');
  const [selectedParam, setSelectedParam] = useState<SensitivityParameterLegacy | null>(null);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      const simulationData = await api.getSimulation(simulationId);

      if (simulationData) {
        setCurrentSimulation(simulationData);

        // Try to get real sensitivity analysis from API
        const sensitivityData = await api.getSensitivityAnalysis(simulationId);
        if (sensitivityData) {
          setChartData(convertApiDataToChart(sensitivityData));
        } else {
          // Fall back to mock data if API fails
          setChartData(generateMockSensitivityData());
        }
      }
      setIsLoading(false);
    };

    loadSimulation();
  }, [simulationId, setCurrentSimulation]);

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

  if (!currentSimulation || !chartData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Simulation not found</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <Link href={`/simulations/${simulationId}`}>
              <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
                Back
              </Button>
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

              <div className="overflow-x-auto">
                <div className="min-w-[600px]">
                  <TornadoChart
                    data={chartData}
                    width={900}
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
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 text-sm text-slate-300">
                <div>
                  <h3 className="font-medium text-slate-200 mb-2">Reading the Chart</h3>
                  <ul className="space-y-2 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Bars extending to the <strong>right</strong> indicate parameters that increase the outcome when their values increase
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Bars extending to the <strong>left</strong> indicate parameters that decrease the outcome when their values decrease
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Longer bars represent higher sensitivity (greater impact on the outcome)
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-medium text-slate-200 mb-2">Key Insights</h3>
                  <ul className="space-y-2 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Focus risk management efforts on parameters with the longest bars
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Parameters near the top of the chart drive the most variance in outcomes
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">•</span>
                      Consider scenario planning around high-impact parameters
                    </li>
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
