'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Brain, TrendingUp, Shield, Lightbulb, Users, BarChart3, CheckCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type { CrossSimulationPattern, PrivacyReport, ArchetypeImprovement } from '@/lib/types';

// Mock data
const mockPatterns: CrossSimulationPattern = {
  total_simulations: 47,
  patterns: {
    archetype_decisions: {
      aggressor: {
        average_support_rate: 0.72,
        sample_size: 156,
        confidence: 0.89,
      },
      defender: {
        average_support_rate: 0.58,
        sample_size: 142,
        confidence: 0.85,
      },
      mediator: {
        average_support_rate: 0.81,
        sample_size: 128,
        confidence: 0.91,
      },
      analyst: {
        average_support_rate: 0.69,
        sample_size: 134,
        confidence: 0.87,
      },
    },
    coalition_formations: {
      'aggressor-mediator': { frequency: 0.34 },
      'defender-analyst': { frequency: 0.28 },
      'mediator-analyst': { frequency: 0.22 },
    },
    environment_outcomes: {
      corporate: {
        average_rounds: 8.5,
        consensus_rate: 0.67,
        sample_size: 23,
      },
      crisis: {
        average_rounds: 5.2,
        consensus_rate: 0.45,
        sample_size: 12,
      },
      market: {
        average_rounds: 11.3,
        consensus_rate: 0.52,
        sample_size: 12,
      },
    },
  },
};

const mockPrivacyReport: PrivacyReport = {
  simulation_id: 'sim-1',
  opted_in: true,
  data_points_shared: 156,
  categories: {
    decisions: 45,
    outcomes: 38,
    patterns: 73,
  },
  anonymization_method: 'differential_privacy',
  privacy_epsilon: 0.1,
  shared_at: '2024-01-15T10:00:00Z',
};

const mockImprovements: Record<string, ArchetypeImprovement> = {
  aggressor: {
    parameter: 'risk_tolerance',
    suggested_value: 0.75,
    current_estimate: 0.68,
    confidence: 0.82,
    sample_size: 156,
    rationale: 'Based on cross-simulation analysis, aggressor archetypes show higher success rates with slightly elevated risk tolerance in M&A scenarios.',
  },
  defender: {
    parameter: 'coalition_tendencies',
    suggested_value: 0.62,
    current_estimate: 0.55,
    confidence: 0.78,
    sample_size: 142,
    rationale: 'Defender archetypes benefit from increased coalition formation, particularly with analyst types in regulatory scenarios.',
  },
};

export default function CrossSimulationPage() {
  const [patterns, setPatterns] = useState<CrossSimulationPattern | null>(null);
  const [privacyReport, setPrivacyReport] = useState<PrivacyReport | null>(null);
  const [improvements, setImprovements] = useState<Record<string, ArchetypeImprovement>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [optInEnabled, setOptInEnabled] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [patternsData, privacyData, improvementsData] = await Promise.all([
          api.getCrossSimulationPatterns(),
          api.getPrivacyReport('sim-1'),
          api.getArchetypeImprovements(),
        ]);
        setPatterns(patternsData);
        setPrivacyReport(privacyData);
        setImprovements(improvementsData.suggestions || {});
      } catch {
        setPatterns(mockPatterns);
        setPrivacyReport(mockPrivacyReport);
        setImprovements(mockImprovements);
      }
      setIsLoading(false);
    };

    loadData();
  }, []);

  const handleOptInToggle = async () => {
    const newValue = !optInEnabled;
    setOptInEnabled(newValue);
    try {
      await api.crossSimulationOptIn('sim-1');
    } catch {
      // Mock success
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading cross-simulation analytics...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Cross-Simulation Learning</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Aggregate insights from {patterns?.total_simulations || 0} simulations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Opt-in to share data:</span>
          <button
            onClick={handleOptInToggle}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              optInEnabled ? 'bg-accent' : 'bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                optInEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Privacy Report */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-100">Privacy Report</h2>
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-slate-700/20 rounded-lg text-center">
            <div className="text-2xl font-bold text-slate-100">{privacyReport?.data_points_shared || 0}</div>
            <div className="text-sm text-slate-400">Data Points Shared</div>
          </div>
          <div className="p-4 bg-slate-700/20 rounded-lg text-center">
            <div className="text-2xl font-bold text-slate-100">{privacyReport?.anonymization_method || 'N/A'}</div>
            <div className="text-sm text-slate-400">Anonymization</div>
          </div>
          <div className="p-4 bg-slate-700/20 rounded-lg text-center">
            <div className="text-2xl font-bold text-slate-100">ε = {privacyReport?.privacy_epsilon || 0}</div>
            <div className="text-sm text-slate-400">Privacy Budget</div>
          </div>
          <div className="p-4 bg-slate-700/20 rounded-lg text-center">
            <div className="text-2xl font-bold text-green-400">
              {privacyReport?.opted_in ? 'Active' : 'Inactive'}
            </div>
            <div className="text-sm text-slate-400">Status</div>
          </div>
        </div>
      </Card>

      {/* Archetype Patterns */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-100">Archetype Decision Patterns</h2>
          </div>
        }
      >
        <div className="space-y-4">
          {Object.entries(patterns?.patterns.archetype_decisions || {}).map(([archetype, data]) => (
            <div key={archetype} className="p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-slate-200 capitalize">{archetype}</span>
                <span className="text-sm text-slate-400">n = {data.sample_size}</span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-slate-400">Average Support Rate</span>
                    <span className="text-slate-200">{(data.average_support_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full"
                      style={{ width: `${data.average_support_rate * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-sm text-slate-500">
                  {(data.confidence * 100).toFixed(0)}% confidence
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Coalition Patterns */}
      {patterns?.patterns.coalition_formations && (
        <Card
          header={
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-semibold text-slate-100">Coalition Formation Patterns</h2>
            </div>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(patterns.patterns.coalition_formations).map(([coalition, data]) => (
              <div key={coalition} className="p-4 bg-slate-700/20 rounded-lg">
                <div className="text-sm text-slate-400 mb-1">{coalition.replace('-', ' + ')}</div>
                <div className="text-2xl font-bold text-slate-100">
                  {(data.frequency * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-slate-500">formation rate</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Environment Outcomes */}
      {patterns?.patterns.environment_outcomes && (
        <Card
          header={
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-semibold text-slate-100">Environment Outcomes</h2>
            </div>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Environment</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Avg Rounds</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Consensus Rate</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Sample Size</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {Object.entries(patterns.patterns.environment_outcomes).map(([env, data]) => (
                  <tr key={env} className="hover:bg-slate-700/20">
                    <td className="py-3 px-4 text-sm font-medium text-slate-200 capitalize">{env}</td>
                    <td className="py-3 px-4 text-sm text-slate-300">{data.average_rounds}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent rounded-full"
                            style={{ width: `${data.consensus_rate * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-slate-300">{(data.consensus_rate * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-400">{data.sample_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Archetype Improvement Suggestions */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-100">Archetype Improvement Suggestions</h2>
          </div>
        }
      >
        <div className="space-y-4">
          {Object.entries(improvements).map(([archetype, improvement]) => (
            <div key={archetype} className="p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <span className="font-medium text-slate-200 capitalize">{archetype}</span>
                  <span className="text-slate-400 mx-2">→</span>
                  <span className="text-sm text-slate-400">{improvement.parameter}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-500">{(improvement.confidence * 100).toFixed(0)}% confidence</span>
                  <CheckCircle className="w-4 h-4 text-green-400" />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-2">
                <div className="text-sm">
                  <span className="text-slate-500">Current: </span>
                  <span className="text-slate-300">{improvement.current_estimate.toFixed(2)}</span>
                </div>
                <div className="text-sm">
                  <span className="text-slate-500">Suggested: </span>
                  <span className="text-accent font-medium">{improvement.suggested_value.toFixed(2)}</span>
                </div>
                <div className="text-sm text-slate-500">
                  n = {improvement.sample_size}
                </div>
              </div>
              <p className="text-sm text-slate-400">{improvement.rationale}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
