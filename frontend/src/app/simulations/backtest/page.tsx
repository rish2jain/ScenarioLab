'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { BacktestCase, BacktestResult } from '@/lib/types';

export default function BacktestPage() {
  const [cases, setCases] = useState<BacktestCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [casesLoading, setCasesLoading] = useState(true);
  const [customMode, setCustomMode] = useState(false);
  const [customSeed, setCustomSeed] = useState('');
  const [customOutcomes, setCustomOutcomes] = useState('');

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    setLoadError(null);
    setCasesLoading(true);
    try {
      const caseList = await api.getBacktestCases();
      setCases(caseList);
      setSelectedCase((prev) => {
        if (prev == null) return null;
        return caseList.some((c) => c.case_id === prev) ? prev : null;
      });
    } catch (err) {
      setCases([]);
      setSelectedCase(null);
      setLoadError(
        err instanceof Error ? err.message : 'Failed to load backtest cases.'
      );
    } finally {
      setCasesLoading(false);
    }
  };

  const runBacktest = async () => {
    setLoading(true);
    try {
      let res: BacktestResult;
      if (customMode) {
        res = await api.runBacktest({
          seed_material: customSeed,
          actual_outcomes: customOutcomes ? JSON.parse(customOutcomes) : undefined,
        });
      } else {
        res = await api.runBacktest({ case_id: selectedCase || undefined });
      }
      setResult(res);
    } catch (err) {
      console.error('Backtest failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const getAccuracyColor = (score: number): string => {
    if (score >= 0.7) return 'bg-green-500';
    if (score >= 0.4) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getAccuracyTextColor = (score: number): string => {
    if (score >= 0.7) return 'text-green-600';
    if (score >= 0.4) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Simulation Backtesting
          </h1>
          <p className="mt-2 text-gray-600">
            Validate simulation accuracy against historical case studies
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Case Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Select Test Case</h2>

            <div className="flex gap-4 mb-4">
              <button
                onClick={() => setCustomMode(false)}
                className={`px-4 py-2 rounded ${
                  !customMode
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                Bundled Cases
              </button>
              <button
                onClick={() => setCustomMode(true)}
                className={`px-4 py-2 rounded ${
                  customMode
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                Custom Case
              </button>
            </div>

            {!customMode ? (
              <div className="space-y-3">
                {loadError ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 space-y-3">
                    <p>{loadError}</p>
                    <button
                      type="button"
                      onClick={() => void loadCases()}
                      disabled={casesLoading}
                      className="rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 ring-1 ring-inset ring-red-200 hover:bg-red-200 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {casesLoading ? 'Retrying…' : 'Retry'}
                    </button>
                  </div>
                ) : casesLoading ? (
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
                    Loading cases…
                  </div>
                ) : (
                  cases.map((c) => (
                    <div
                      key={c.case_id}
                      onClick={() => setSelectedCase(c.case_id)}
                      className={`p-4 border rounded-lg cursor-pointer transition ${
                        selectedCase === c.case_id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <h3 className="font-medium">{c.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {c.description}
                      </p>
                      <div className="flex gap-2 mt-2">
                        {c.tags.map((tag) => (
                          <span
                            key={tag}
                            className="text-xs bg-gray-100 px-2 py-1 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Seed Material
                  </label>
                  <textarea
                    value={customSeed}
                    onChange={(e) => setCustomSeed(e.target.value)}
                    rows={6}
                    className="w-full border rounded-lg p-3 text-sm"
                    placeholder="Enter historical context/seed material..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Actual Outcomes (JSON)
                  </label>
                  <textarea
                    value={customOutcomes}
                    onChange={(e) => setCustomOutcomes(e.target.value)}
                    rows={4}
                    className="w-full border rounded-lg p-3 text-sm font-mono"
                    placeholder='{"stakeholder_stances": {}, "timeline": {}, "outcome_direction": {}}'
                  />
                </div>
              </div>
            )}

            <button
              onClick={runBacktest}
              disabled={loading || (!customMode && (!selectedCase || !!loadError))}
              className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-medium disabled:bg-gray-400 disabled:cursor-not-allowed hover:bg-blue-700 transition"
            >
              {loading ? 'Running Backtest...' : 'Run Backtest'}
            </button>
          </div>

          {/* Results */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Results</h2>

            {!result ? (
              <div className="text-center py-12 text-gray-500">
                <p>Select a case and run backtest to see results</p>
              </div>
            ) : result.error ? (
              <div className="bg-red-50 text-red-700 p-4 rounded-lg">
                {result.error}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Overall Score */}
                <div className="text-center p-6 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600 mb-2">
                    Overall Accuracy
                  </p>
                  <p
                    className={`text-5xl font-bold ${getAccuracyTextColor(
                      result.comparison.overall_accuracy
                    )}`}
                  >
                    {(result.comparison.overall_accuracy * 100).toFixed(1)}%
                  </p>
                </div>

                {/* Rubric Scores */}
                <div>
                  <h3 className="font-medium mb-3">Rubric Breakdown</h3>
                  <div className="space-y-3">
                    {Object.entries(result.comparison.rubric_scores).map(
                      ([key, value]) => (
                        <div key={key}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="capitalize">
                              {key.replace(/_/g, ' ')}
                            </span>
                            <span className="font-medium">
                              {(value * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${getAccuracyColor(value)}`}
                              style={{ width: `${value * 100}%` }}
                            />
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* Stance Comparison */}
                {result.comparison.detailed_analysis.stance_comparison.length >
                  0 && (
                  <div>
                    <h3 className="font-medium mb-3">Stakeholder Stances</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">Stakeholder</th>
                            <th className="text-left py-2">Simulated</th>
                            <th className="text-left py-2">Actual</th>
                            <th className="text-center py-2">Match</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.comparison.detailed_analysis.stance_comparison.map(
                            (item, idx) => (
                              <tr key={idx} className="border-b">
                                <td className="py-2 capitalize">
                                  {item.stakeholder}
                                </td>
                                <td className="py-2 text-gray-600">
                                  {item.simulated}
                                </td>
                                <td className="py-2 text-gray-600">
                                  {item.actual}
                                </td>
                                <td className="py-2 text-center">
                                  <span
                                    className={`px-2 py-1 rounded text-xs ${
                                      item.match === 'match'
                                        ? 'bg-green-100 text-green-700'
                                        : item.match === 'mismatch'
                                          ? 'bg-red-100 text-red-700'
                                          : 'bg-gray-100 text-gray-700'
                                    }`}
                                  >
                                    {item.match}
                                  </span>
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="text-sm text-gray-500 pt-4 border-t">
                  <p>Simulation ID: {result.simulation_id}</p>
                  <p>Status: {result.status}</p>
                  <p>Timestamp: {result.timestamp}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
