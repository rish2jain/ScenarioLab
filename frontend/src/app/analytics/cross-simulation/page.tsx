'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Brain, TrendingUp, Shield, Lightbulb, Users, BarChart3, CheckCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { useToast } from '@/components/ui/Toast';
import { api, loadSimulationsFromApi } from '@/lib/api';
import type { CrossSimulationPattern, PrivacyReport, ArchetypeImprovement } from '@/lib/types';

type ApiLoadErrorKind = 'unavailable' | 'unexpected';

function classifyCrossSimulationLoadError(error: unknown): ApiLoadErrorKind {
  if (error instanceof TypeError) {
    return 'unavailable';
  }
  const msg = error instanceof Error ? error.message : String(error);
  if (/failed to fetch|networkerror|load failed|aborted|connection refused|econnrefused/i.test(msg)) {
    return 'unavailable';
  }
  return 'unexpected';
}

export default function CrossSimulationPage() {
  const { addToast } = useToast();
  const [patterns, setPatterns] = useState<CrossSimulationPattern | null>(null);
  const [privacyReport, setPrivacyReport] = useState<PrivacyReport | null>(null);
  const [improvements, setImprovements] = useState<Record<string, ArchetypeImprovement>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [targetSimulationId, setTargetSimulationId] = useState<string | null>(null);
  const [apiLoadError, setApiLoadError] = useState<ApiLoadErrorKind | null>(null);
  const [isOptingIn, setIsOptingIn] = useState(false);
  const optInInFlightRef = useRef(false);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      let candidateSimulationId: string | null = null;
      try {
        setApiLoadError(null);
        const simRes = await loadSimulationsFromApi();
        if (!simRes.ok) {
          addToast('Could not load simulations. Check that the API is running.', 'error');
        }
        const simulations = simRes.ok ? (simRes.simulations ?? []) : [];
        candidateSimulationId =
          simulations.find((simulation) => simulation.status === 'completed' || simulation.status === 'failed')?.id
          ?? simulations[0]?.id
          ?? null;
        setTargetSimulationId(candidateSimulationId);

        const [patternsData, improvementsData, privacyData] = await Promise.all([
          api.getCrossSimulationPatterns(),
          api.getArchetypeImprovements(),
          candidateSimulationId ? api.getPrivacyReport(candidateSimulationId) : Promise.resolve(null),
        ]);
        setPatterns(patternsData);
        setPrivacyReport(privacyData);
        setImprovements(improvementsData.suggestions || {});
      } catch (error: unknown) {
        const kind = classifyCrossSimulationLoadError(error);
        setApiLoadError(kind);
        console.error(
          '[cross-simulation] Failed to load patterns, archetype improvements, or privacy report.',
          { simulationId: candidateSimulationId ?? '(none)', kind, error }
        );
        if (kind === 'unavailable') {
          addToast(
            `Cross-simulation API unreachable (simulation: ${candidateSimulationId ?? 'n/a'}).`,
            'error'
          );
        } else {
          addToast(
            `Unexpected error loading cross-simulation analytics (simulation: ${candidateSimulationId ?? 'n/a'}).`,
            'error'
          );
        }
        setPatterns(null);
        setPrivacyReport(null);
        setImprovements({});
      }
      setIsLoading(false);
    };

    loadData();
  }, [addToast]);

  const handleOptInToggle = async () => {
    if (isOptingIn) return;
    if (optInInFlightRef.current) return;
    if (!targetSimulationId || privacyReport?.opted_in) return;

    optInInFlightRef.current = true;
    setIsOptingIn(true);
    try {
      const result = await api.crossSimulationOptIn(targetSimulationId);
      setPrivacyReport((prev) =>
        prev
          ? { ...prev, opted_in: result.opted_in }
          : {
              simulation_id: result.simulation_id,
              opted_in: result.opted_in,
              data_points_shared: 0,
              categories: {},
              anonymization_method: 'differential_privacy',
              privacy_epsilon: 0.1,
              shared_at: new Date().toISOString(),
            }
      );
    } catch (error) {
      console.error('Opt-in failed:', error);
      const message =
        error instanceof Error && error.message
          ? `Failed to opt in to cross-simulation sharing: ${error.message}`
          : 'Failed to opt in to cross-simulation sharing.';
      addToast(message, 'error');
    } finally {
      optInInFlightRef.current = false;
      setIsOptingIn(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading cross-simulation analytics...</div>
      </div>
    );
  }

  const hasData = (patterns?.total_simulations || 0) > 0;

  const optInEnabled = Boolean(privacyReport?.opted_in);

  return (
    <div className="space-y-6 animate-fade-in">
      {apiLoadError && (
        <div
          role="alert"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
        >
          {apiLoadError === 'unavailable'
            ? 'Cross-simulation API was unreachable. No sample data is being shown.'
            : 'An unexpected error occurred while loading cross-simulation analytics.'}
        </div>
      )}
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
            disabled={isOptingIn || !targetSimulationId || optInEnabled}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              optInEnabled ? 'bg-accent' : 'bg-slate-600'
            } ${
              isOptingIn || !targetSimulationId || optInEnabled
                ? 'cursor-not-allowed opacity-60'
                : ''
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

      <Card padding="md">
        <p className="text-sm text-slate-400">
          Compare two environment presets with the same roster and seeds: call{' '}
          <code className="text-slate-300">POST /api/simulations/dual-run-preset</code>{' '}
          (returns <code className="text-slate-300">batch_parent_id</code> and two create payloads),
          then create both simulations and analyze them here. Start from{' '}
          <Link href="/simulations/new" className="text-accent hover:underline">
            New simulation
          </Link>
          .
        </p>
      </Card>

      {!hasData ? (
        <Card padding="lg">
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <Brain className="w-12 h-12 text-slate-500 mb-4" />
            <h2 className="text-xl font-bold text-slate-200">Insufficient Data</h2>
            <p className="text-slate-400 mt-2 max-w-md">
              Cross-simulation learning requires completed simulations to identify patterns and insights. Check back once more simulations have finished.
            </p>
          </div>
        </Card>
      ) : (
        <>
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
        {Object.keys(improvements).length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <Lightbulb className="w-8 h-8 text-slate-500 mb-4 opacity-50" />
            <h2 className="text-lg font-semibold text-slate-200">Insufficient Data</h2>
            <p className="text-sm text-slate-400 mt-2">
              No improvement suggestions available yet.
            </p>
          </div>
        ) : (
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
        )}
      </Card>
        </>
      )}
    </div>
  );
}
