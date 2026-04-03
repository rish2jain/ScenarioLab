'use client';

import { clsx } from 'clsx';
import type { Stakeholder } from '@/lib/types';

interface StakeholderHeatmapProps {
  stakeholders: Stakeholder[];
}

export function StakeholderHeatmap({ stakeholders }: StakeholderHeatmapProps) {
  const getSupportColor = (level: number) => {
    // level ranges from -100 to 100
    if (level >= 50) return 'bg-green-500';
    if (level >= 20) return 'bg-green-400';
    if (level >= 0) return 'bg-green-300';
    if (level >= -20) return 'bg-amber-400';
    if (level >= -50) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getSupportLabel = (level: number) => {
    if (level >= 50) return 'Strong Support';
    if (level >= 20) return 'Supportive';
    if (level >= 0) return 'Neutral';
    if (level >= -20) return 'Concerned';
    if (level >= -50) return 'Opposed';
    return 'Strongly Opposed';
  };

  const getInfluenceSize = (influence: string) => {
    switch (influence) {
      case 'high':
        return 'w-16 h-16';
      case 'medium':
        return 'w-12 h-12';
      case 'low':
        return 'w-8 h-8';
      default:
        return 'w-12 h-12';
    }
  };

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <span className="text-sm font-medium text-slate-300">Support Level:</span>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded" />
          <span className="text-xs text-slate-400">Strong Support</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-400 rounded" />
          <span className="text-xs text-slate-400">Supportive</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-300 rounded" />
          <span className="text-xs text-slate-400">Neutral</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-amber-400 rounded" />
          <span className="text-xs text-slate-400">Concerned</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-500 rounded" />
          <span className="text-xs text-slate-400">Opposed</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded" />
          <span className="text-xs text-slate-400">Strongly Opposed</span>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stakeholders.map((stakeholder) => (
          <div
            key={stakeholder.id}
            className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors"
          >
            <div className="flex items-start gap-4">
              {/* Influence Indicator */}
              <div className="flex flex-col items-center">
                <div
                  className={clsx(
                    'rounded-full flex items-center justify-center',
                    getSupportColor(stakeholder.supportLevel),
                    getInfluenceSize(stakeholder.influence)
                  )}
                >
                  <span className="text-slate-900 font-bold text-sm">
                    {stakeholder.supportLevel > 0 ? '+' : ''}
                    {stakeholder.supportLevel}
                  </span>
                </div>
                <span className="text-xs text-slate-500 mt-1 capitalize">
                  {stakeholder.influence} Influence
                </span>
              </div>

              {/* Stakeholder Info */}
              <div className="flex-1">
                <h4 className="font-semibold text-slate-200">{stakeholder.name}</h4>
                <p className="text-sm text-slate-400">{stakeholder.role}</p>
                <div className="mt-2">
                  <span
                    className={clsx(
                      'inline-block px-2 py-0.5 rounded text-xs font-medium',
                      getSupportColor(stakeholder.supportLevel),
                      'bg-opacity-20 text-white'
                    )}
                  >
                    {getSupportLabel(stakeholder.supportLevel)}
                  </span>
                </div>

                {/* Concerns */}
                {stakeholder.concerns.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                      Key Concerns
                    </p>
                    <ul className="space-y-1">
                      {stakeholder.concerns.map((concern, idx) => (
                        <li
                          key={idx}
                          className="text-xs text-slate-400 flex items-start gap-1"
                        >
                          <span className="text-slate-600">•</span>
                          {concern}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 text-center">
          <p className="text-2xl font-bold text-green-400">
            {stakeholders.filter((s) => s.supportLevel >= 20).length}
          </p>
          <p className="text-xs text-slate-400 mt-1">Supportive</p>
        </div>
        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 text-center">
          <p className="text-2xl font-bold text-slate-300">
            {stakeholders.filter((s) => s.supportLevel >= 0 && s.supportLevel < 20).length}
          </p>
          <p className="text-xs text-slate-400 mt-1">Neutral</p>
        </div>
        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 text-center">
          <p className="text-2xl font-bold text-orange-400">
            {stakeholders.filter((s) => s.supportLevel < 0 && s.supportLevel > -50).length}
          </p>
          <p className="text-xs text-slate-400 mt-1">Opposed</p>
        </div>
        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 text-center">
          <p className="text-2xl font-bold text-accent">
            {stakeholders.filter((s) => s.influence === 'high').length}
          </p>
          <p className="text-xs text-slate-400 mt-1">High Influence</p>
        </div>
      </div>
    </div>
  );
}
