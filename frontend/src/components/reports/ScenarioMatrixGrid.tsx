'use client';

import { clsx } from 'clsx';
import type { Scenario } from '@/lib/types';

interface ScenarioMatrixGridProps {
  scenarios: Scenario[];
}

export function ScenarioMatrixGrid({ scenarios }: ScenarioMatrixGridProps) {
  const getProbabilityColor = (probability: number) => {
    if (probability >= 0.5) return 'bg-green-500/30 text-green-300 border-green-500/50';
    if (probability >= 0.3) return 'bg-blue-500/30 text-blue-300 border-blue-500/50';
    if (probability >= 0.15) return 'bg-amber-500/30 text-amber-300 border-amber-500/50';
    return 'bg-slate-500/30 text-slate-300 border-slate-500/50';
  };

  const getOutcomeColor = (probability: number) => {
    if (probability >= 0.6) return 'bg-green-500';
    if (probability >= 0.4) return 'bg-blue-500';
    if (probability >= 0.2) return 'bg-amber-500';
    return 'bg-slate-500';
  };

  return (
    <div className="space-y-6">
      {/* Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scenarios.map((scenario) => (
          <div
            key={scenario.id}
            className={clsx(
              'p-4 rounded-lg border-2 transition-all',
              getProbabilityColor(scenario.probability)
            )}
          >
            <div className="flex items-start justify-between mb-3">
              <h4 className="font-semibold">{scenario.name}</h4>
              <span className="text-lg font-bold">
                {(scenario.probability * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm opacity-80 mb-4">{scenario.description}</p>
            
            {/* Outcome Distribution */}
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wider opacity-70">Outcome Distribution</p>
              <div className="flex h-4 rounded-full overflow-hidden">
                {Object.entries(scenario.outcomes).map(([outcome, prob]) => (
                  <div
                    key={outcome}
                    className={clsx('h-full', getOutcomeColor(prob))}
                    style={{ width: `${prob * 100}%` }}
                    title={`${outcome}: ${(prob * 100).toFixed(0)}%`}
                  />
                ))}
              </div>
              <div className="flex flex-wrap gap-3 text-xs">
                {Object.entries(scenario.outcomes).map(([outcome, prob]) => (
                  <div key={outcome} className="flex items-center gap-1">
                    <div className={clsx('w-2 h-2 rounded-full', getOutcomeColor(prob))} />
                    <span className="capitalize">{outcome}</span>
                    <span className="opacity-70">({(prob * 100).toFixed(0)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Matrix Visualization */}
      <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-6">
        <h4 className="font-semibold text-slate-200 mb-4">Scenario Impact Matrix</h4>
        <div className="relative">
          {/* Grid */}
          <div className="grid grid-cols-4 gap-2">
            {/* Header Row */}
            <div className="p-3"></div>
            <div className="p-3 text-center text-sm font-medium text-slate-400">Low Impact</div>
            <div className="p-3 text-center text-sm font-medium text-slate-400">Medium Impact</div>
            <div className="p-3 text-center text-sm font-medium text-slate-400">High Impact</div>

            {/* High Probability Row */}
            <div className="p-3 flex items-center text-sm font-medium text-slate-400">High Prob</div>
            <div className="p-4 bg-green-500/20 border border-green-500/30 rounded-lg min-h-[80px]">
              {scenarios.filter(s => s.probability >= 0.4 && Object.values(s.outcomes).some(o => o >= 0.4 && o < 0.6)).map(s => (
                <div key={s.id} className="text-xs text-green-300 mb-1">{s.name}</div>
              ))}
            </div>
            <div className="p-4 bg-amber-500/20 border border-amber-500/30 rounded-lg min-h-[80px]">
              {scenarios.filter(s => s.probability >= 0.4 && Object.values(s.outcomes).some(o => o >= 0.3 && o < 0.5)).map(s => (
                <div key={s.id} className="text-xs text-amber-300 mb-1">{s.name}</div>
              ))}
            </div>
            <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg min-h-[80px]">
              {scenarios.filter(s => s.probability >= 0.4 && Object.values(s.outcomes).some(o => o < 0.3)).map(s => (
                <div key={s.id} className="text-xs text-red-300 mb-1">{s.name}</div>
              ))}
            </div>

            {/* Medium Probability Row */}
            <div className="p-3 flex items-center text-sm font-medium text-slate-400">Med Prob</div>
            <div className="p-4 bg-blue-500/20 border border-blue-500/30 rounded-lg min-h-[80px]"></div>
            <div className="p-4 bg-slate-500/20 border border-slate-500/30 rounded-lg min-h-[80px]"></div>
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg min-h-[80px]"></div>

            {/* Low Probability Row */}
            <div className="p-3 flex items-center text-sm font-medium text-slate-400">Low Prob</div>
            <div className="p-4 bg-slate-500/10 border border-slate-500/20 rounded-lg min-h-[80px]"></div>
            <div className="p-4 bg-slate-500/10 border border-slate-500/20 rounded-lg min-h-[80px]"></div>
            <div className="p-4 bg-slate-500/10 border border-slate-500/20 rounded-lg min-h-[80px]"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
