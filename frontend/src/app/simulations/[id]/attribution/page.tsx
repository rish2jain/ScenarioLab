'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, PieChart, Info, Users, Database } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type { AttributionResult } from '@/lib/types';

const AGENT_COLORS = [
  '#14b8a6', '#f59e0b', '#3b82f6', '#8b5cf6',
  '#ef4444', '#22c55e', '#ec4899', '#06b6d4',
];

export default function AttributionPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';

  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadAttribution = async () => {
      setIsLoading(true);
      try {
        const result = await api.getAttribution(simulationId);
        setAttribution(result ?? null);
      } catch (err) {
        console.error('Failed to load attribution analysis', err);
        setAttribution(null);
      }
      setIsLoading(false);
    };

    loadAttribution();
  }, [simulationId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading attribution analysis...</div>
      </div>
    );
  }

  const agents = attribution?.agent_attributions ?? [];

  if (!attribution || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center space-y-4">
        <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mb-2">
          <Database className="w-8 h-8 text-slate-500" />
        </div>
        <h2 className="text-xl font-semibold text-slate-200">Insufficient Data for Attribution Analysis</h2>
        <p className="text-slate-400 max-w-md">
          Not enough simulation rounds have been completed to generate statistically significant Shapley values.
          Please wait for the simulation to progress further.
        </p>
        <Link href={`/simulations/${simulationId}`}>
          <Button variant="secondary" className="mt-4">Return to Overview</Button>
        </Link>
      </div>
    );
  }

  const sortedAgents = [...agents].sort((a, b) => b.attribution_score - a.attribution_score);
  const maxScore = sortedAgents.length > 0 ? sortedAgents[0].attribution_score : 1;
  const coalitions = attribution.coalition_attributions ?? [];

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
                Attribution Analysis
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                Shapley-based outcome attribution
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Agent Attribution Chart */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <PieChart className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">
                  Agent Attribution Scores
                </h2>
              </div>
            }
          >
            <div className="space-y-4">
              {sortedAgents.map((agent, idx) => {
                const color = AGENT_COLORS[idx % AGENT_COLORS.length];
                const pct = agent.attribution_score * 100;
                const ciPair =
                  Array.isArray(agent.confidence_interval) &&
                  agent.confidence_interval.length >= 2
                    ? agent.confidence_interval
                    : null;
                const ciLo = ciPair?.[0];
                const ciHi = ciPair?.[1];
                return (
                  <div key={agent.agent_id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        <span className="text-sm font-medium text-slate-200">
                          {agent.agent_name}
                        </span>
                        <span className="text-xs text-slate-500">{agent.role}</span>
                      </div>
                      <span className="text-sm font-bold text-slate-100 w-16 text-right">
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-4 bg-slate-700/50 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${maxScore > 0 ? (agent.attribution_score / maxScore) * 100 : 0}%`,
                          backgroundColor: color,
                        }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500">
                        {typeof ciLo === 'number' && typeof ciHi === 'number' ? (
                          <>
                            Confidence: {(ciLo * 100).toFixed(0)}%–{(ciHi * 100).toFixed(0)}%
                          </>
                        ) : (
                          <>Confidence: —</>
                        )}
                      </span>
                      {Array.isArray(agent.key_contributions) &&
                        agent.key_contributions.length > 0 && (
                        <span className="text-slate-400 truncate max-w-[60%] text-right">
                          {agent.key_contributions[0]}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Coalition Attribution */}
          {coalitions.length > 0 && (
            <Card
              header={
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-accent" />
                  <h2 className="text-lg font-semibold text-slate-100">
                    Coalition Attribution
                  </h2>
                </div>
              }
            >
              <div className="space-y-4">
                {coalitions.map((c) => (
                  <div key={c.coalition_id} className="p-4 bg-slate-700/20 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-slate-200">{c.coalition_id}</span>
                      <span className="text-lg font-bold text-accent">
                        {(c.attribution_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {(c.member_names ?? []).map((name, idx) => (
                        <span
                          key={`${c.coalition_id}-${idx}`}
                          className="px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-300"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                    {c.key_influence && (
                      <p className="text-sm text-slate-400">{c.key_influence}</p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Methodology */}
          <Card>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-slate-400 mt-0.5" />
              <div>
                <h3 className="font-medium text-slate-200 mb-1">Methodology</h3>
                <p className="text-sm text-slate-400">
                  {attribution.methodology_note || 'Shapley value-based attribution analysis'}
                </p>
                {attribution.outcome_metric && (
                  <p className="text-xs text-slate-500 mt-1">
                    Outcome metric: {attribution.outcome_metric}
                  </p>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
