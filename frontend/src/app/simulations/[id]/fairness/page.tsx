'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Scale, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface FairnessMetric {
  name: string;
  value: number;
  threshold: number;
  p_value: number;
  passed: boolean;
  description: string;
}

interface FairnessAuditResult {
  overall_score: number;
  metrics: FairnessMetric[];
  recommendations: string[];
  methodology: string;
}

// Mock fairness audit data
const mockFairnessAudit: FairnessAuditResult = {
  overall_score: 0.78,
  metrics: [
    {
      name: 'Demographic Parity',
      value: 0.15,
      threshold: 0.20,
      p_value: 0.032,
      passed: true,
      description: 'Measures if outcomes are independent of protected attributes',
    },
    {
      name: 'Equal Opportunity',
      value: 0.08,
      threshold: 0.15,
      p_value: 0.089,
      passed: true,
      description: 'Ensures equal true positive rates across groups',
    },
    {
      name: 'Calibration',
      value: 0.22,
      threshold: 0.25,
      p_value: 0.156,
      passed: true,
      description: 'Checks if predicted probabilities match observed frequencies',
    },
    {
      name: 'Individual Fairness',
      value: 0.31,
      threshold: 0.25,
      p_value: 0.008,
      passed: false,
      description: 'Similar individuals should receive similar outcomes',
    },
    {
      name: 'Counterfactual Fairness',
      value: 0.12,
      threshold: 0.20,
      p_value: 0.045,
      passed: true,
      description: 'Outcomes would not change if protected attributes differed',
    },
  ],
  recommendations: [
    'Review agent decision logic for individual fairness violations in rounds 4-7',
    'Consider adjusting archetype parameters to reduce bias in coalition formation',
    'Implement additional constraints on decision-making for underrepresented perspectives',
    'Increase diversity in agent archetypes for future simulations',
  ],
  methodology: 'Comprehensive fairness audit using demographic parity, equal opportunity, calibration, individual fairness, and counterfactual fairness metrics with statistical significance testing.',
};

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-400';
  if (score >= 0.6) return 'text-yellow-400';
  return 'text-red-400';
}

function getScoreBg(score: number): string {
  if (score >= 0.8) return 'bg-green-500/20';
  if (score >= 0.6) return 'bg-yellow-500/20';
  return 'bg-red-500/20';
}

export default function FairnessAuditPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';

  const [audit, setAudit] = useState<FairnessAuditResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadAudit = async () => {
      setIsLoading(true);
      try {
        const result = await api.getFairnessAudit(simulationId);
        if (result) {
          setAudit(result);
        } else {
          setAudit(mockFairnessAudit);
        }
      } catch {
        setAudit(mockFairnessAudit);
      }
      setIsLoading(false);
    };

    loadAudit();
  }, [simulationId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading fairness audit...</div>
      </div>
    );
  }

  const passedCount = audit?.metrics.filter(m => m.passed).length || 0;
  const totalCount = audit?.metrics.length || 0;

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
                Fairness Audit
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                Bias detection and fairness metrics
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Overall Score */}
          <Card>
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              <div className={`w-32 h-32 rounded-full ${getScoreBg(audit?.overall_score || 0)} flex items-center justify-center mx-auto md:mx-0`}>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(audit?.overall_score || 0)}`}>
                    {((audit?.overall_score || 0) * 100).toFixed(0)}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Fairness Score</div>
                </div>
              </div>
              <div className="flex-1 text-center md:text-left">
                <h2 className="text-xl font-semibold text-slate-100 mb-2">
                  Overall Fairness Assessment
                </h2>
                <p className="text-slate-400 mb-4">
                  {passedCount} of {totalCount} metrics passed
                </p>
                <div className="flex items-center justify-center md:justify-start gap-2">
                  {(audit?.overall_score || 0) >= 0.8 ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-green-400" />
                      <span className="text-green-400">Fair</span>
                    </>
                  ) : (audit?.overall_score || 0) >= 0.6 ? (
                    <>
                      <AlertTriangle className="w-5 h-5 text-yellow-400" />
                      <span className="text-yellow-400">Needs Attention</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                      <span className="text-red-400">Significant Bias Detected</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Metrics Table */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Fairness Metrics</h2>
              </div>
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Metric</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Value</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Threshold</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">P-Value</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {audit?.metrics.map((metric) => (
                    <tr key={metric.name} className="hover:bg-slate-700/20">
                      <td className="py-3 px-4">
                        <div>
                          <div className="text-sm font-medium text-slate-200">{metric.name}</div>
                          <div className="text-xs text-slate-500 mt-0.5">{metric.description}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-300">
                        {metric.value.toFixed(3)}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-400">
                        {'< '}{metric.threshold.toFixed(3)}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-400">
                        {metric.p_value.toFixed(3)}
                      </td>
                      <td className="py-3 px-4">
                        {metric.passed ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Pass
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            Fail
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Recommendations */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Recommendations</h2>
              </div>
            }
          >
            <ul className="space-y-3">
              {audit?.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-sm font-medium flex-shrink-0 mt-0.5">
                    {index + 1}
                  </div>
                  <span className="text-slate-300">{rec}</span>
                </li>
              ))}
            </ul>
          </Card>

          {/* Methodology */}
          <Card>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-slate-400 mt-0.5" />
              <div>
                <h3 className="font-medium text-slate-200 mb-1">Methodology</h3>
                <p className="text-sm text-slate-400">{audit?.methodology}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
