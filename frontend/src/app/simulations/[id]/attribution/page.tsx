'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, PieChart, Info, Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface AttributionResult {
  agent_attributions: Record<string, {
    score: number;
    confidence: number;
    contribution_type: string;
  }>;
  coalition_attributions?: Record<string, {
    score: number;
    members: string[];
  }>;
  methodology: string;
  confidence_interval: {
    lower: number;
    upper: number;
  };
}

// Mock attribution data
const mockAttribution: AttributionResult = {
  agent_attributions: {
    'agent-1': {
      score: 28.5,
      confidence: 0.92,
      contribution_type: 'strategic_direction',
    },
    'agent-2': {
      score: 22.3,
      confidence: 0.88,
      contribution_type: 'risk_assessment',
    },
    'agent-3': {
      score: 19.7,
      confidence: 0.85,
      contribution_type: 'mediation',
    },
    'agent-4': {
      score: 15.2,
      confidence: 0.79,
      contribution_type: 'operational',
    },
    'agent-5': {
      score: 9.8,
      confidence: 0.71,
      contribution_type: 'supporting',
    },
    'agent-6': {
      score: 4.5,
      confidence: 0.65,
      contribution_type: 'observing',
    },
  },
  coalition_attributions: {
    'Pro-Merger Coalition': {
      score: 48.2,
      members: ['agent-1', 'agent-3', 'agent-5'],
    },
    'Cautious Integration': {
      score: 37.5,
      members: ['agent-2', 'agent-4'],
    },
  },
  methodology: 'Shapley value-based attribution with Monte Carlo sampling for coalition analysis',
  confidence_interval: {
    lower: 0.82,
    upper: 0.94,
  },
};

const agentNames: Record<string, string> = {
  'agent-1': 'Sarah Chen (Acquiring CEO)',
  'agent-2': 'Michael Torres (Target CEO)',
  'agent-3': 'Jennifer Walsh (Integration Lead)',
  'agent-4': 'David Park (HR Director)',
  'agent-5': 'Emma Wilson (Board Member)',
  'agent-6': 'James Liu (Legal Counsel)',
};

const agentColors: Record<string, string> = {
  'agent-1': '#14b8a6',
  'agent-2': '#f59e0b',
  'agent-3': '#3b82f6',
  'agent-4': '#8b5cf6',
  'agent-5': '#ef4444',
  'agent-6': '#22c55e',
};

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
        if (result) {
          setAttribution(result);
        } else {
          setAttribution(mockAttribution);
        }
      } catch {
        setAttribution(mockAttribution);
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

  const sortedAgents = Object.entries(attribution?.agent_attributions || {})
    .sort((a, b) => b[1].score - a[1].score);

  const maxScore = Math.max(...sortedAgents.map(([, data]) => data.score));

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
              {sortedAgents.map(([agentId, data]) => (
                <div key={agentId} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: agentColors[agentId] || '#94a3b8' }}
                      />
                      <span className="text-sm font-medium text-slate-200">
                        {agentNames[agentId] || agentId}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-slate-400">
                        {data.contribution_type}
                      </span>
                      <span className="text-sm font-bold text-slate-100 w-16 text-right">
                        {data.score.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="h-4 bg-slate-700/50 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${(data.score / maxScore) * 100}%`,
                        backgroundColor: agentColors[agentId] || '#94a3b8',
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">
                      Confidence: {(data.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Coalition Attribution */}
          {attribution?.coalition_attributions && (
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
                {Object.entries(attribution.coalition_attributions).map(([coalition, data]) => (
                  <div key={coalition} className="p-4 bg-slate-700/20 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-slate-200">{coalition}</span>
                      <span className="text-lg font-bold text-accent">{data.score.toFixed(1)}%</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {data.members.map((member) => (
                        <span
                          key={member}
                          className="px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-300"
                        >
                          {agentNames[member] || member}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Confidence Interval */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <Info className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">
                  Confidence Interval
                </h2>
              </div>
            }
          >
            <div className="flex items-center gap-4">
              <div className="flex-1 h-8 bg-slate-700/30 rounded-lg relative overflow-hidden">
                <div
                  className="absolute h-full bg-accent/30"
                  style={{
                    left: `${(attribution?.confidence_interval.lower || 0) * 100}%`,
                    right: `${100 - (attribution?.confidence_interval.upper || 1) * 100}%`,
                  }}
                />
                <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-300">
                  {(attribution?.confidence_interval.lower || 0).toFixed(2)} - {(attribution?.confidence_interval.upper || 1).toFixed(2)}
                </div>
              </div>
            </div>
            <p className="text-sm text-slate-400 mt-3">
              95% confidence interval for attribution estimates based on Monte Carlo sampling
            </p>
          </Card>

          {/* Methodology */}
          <Card>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-slate-400 mt-0.5" />
              <div>
                <h3 className="font-medium text-slate-200 mb-1">Methodology</h3>
                <p className="text-sm text-slate-400">
                  {attribution?.methodology || 'Shapley value-based attribution analysis'}
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
