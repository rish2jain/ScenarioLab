'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ChevronLeft,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  Target,
  Users,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type {
  ZOPAResult,
  AgentPosition,
  ConcessionRecommendation,
} from '@/lib/types';

export default function ZOPAPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';

  const [zopaResult, setZopaResult] = useState<ZOPAResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadZOPA = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.analyzeZOPA(simulationId);
        if (data) {
          setZopaResult(data);
        } else {
          setError('Failed to analyze ZOPA. Make sure the simulation is a negotiation type.');
        }
      } catch (err) {
        setZopaResult(null);
        setError(
          err instanceof Error ? err.message : 'Failed to analyze ZOPA.'
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadZOPA();
  }, [simulationId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Analyzing negotiation positions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-4">
          <Link href={`/simulations/${simulationId}`}>
            <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Back to Simulation
            </Button>
          </Link>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!zopaResult) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">No ZOPA data available</div>
      </div>
    );
  }

  const getPositionColor = (flexibility: number): string => {
    if (flexibility >= 0.7) return 'bg-green-500';
    if (flexibility >= 0.4) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getProbabilityColor = (probability: number): string => {
    if (probability >= 0.7) return 'text-red-400';
    if (probability >= 0.4) return 'text-yellow-400';
    return 'text-green-400';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/simulations/${simulationId}`}>
            <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Back to Simulation
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">
              ZOPA Analysis
            </h1>
            <p className="text-slate-400 mt-1">
              Zone of Possible Agreement
            </p>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <Card padding="lg">
        <div className="flex items-start gap-4">
          {zopaResult.zopa_exists ? (
            <CheckCircle className="w-8 h-8 text-green-400 flex-shrink-0" />
          ) : (
            <XCircle className="w-8 h-8 text-red-400 flex-shrink-0" />
          )}
          <div>
            <h2 className="text-lg font-semibold text-slate-100">
              {zopaResult.zopa_exists ? 'ZOPA Identified' : 'No ZOPA Found'}
            </h2>
            <p className="text-slate-300 mt-2">{zopaResult.analysis_summary}</p>
          </div>
        </div>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <Target className="w-6 h-6 text-accent" />
            <div>
              <div className="text-sm text-slate-400">ZOPA Status</div>
              <div className={`text-lg font-semibold ${zopaResult.zopa_exists ? 'text-green-400' : 'text-red-400'}`}>
                {zopaResult.zopa_exists ? 'Exists' : 'No Overlap'}
              </div>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
            <div>
              <div className="text-sm text-slate-400">No-Deal Probability</div>
              <div className={`text-lg font-semibold ${getProbabilityColor(zopaResult.no_deal_probability)}`}>
                {(zopaResult.no_deal_probability * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <Users className="w-6 h-6 text-blue-400" />
            <div>
              <div className="text-sm text-slate-400">Parties Analyzed</div>
              <div className="text-lg font-semibold text-slate-100">
                {zopaResult.positions.length}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Position Visualization */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-accent" />
          Agent Positions
        </h3>
        <div className="space-y-4">
          {zopaResult.positions.map((position) => (
            <PositionBar key={position.agent_id} position={position} getColor={getPositionColor} />
          ))}
        </div>
      </Card>

      {/* ZOPA Boundaries */}
      {zopaResult.zopa_exists && zopaResult.zopa_boundaries && (
        <Card padding="lg">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            ZOPA Boundaries
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-700/50 rounded-lg">
              <div className="text-sm text-slate-400 mb-1">Lower Bound</div>
              <div className="text-slate-200">{zopaResult.zopa_boundaries.lower_bound}</div>
            </div>
            <div className="p-4 bg-slate-700/50 rounded-lg">
              <div className="text-sm text-slate-400 mb-1">Upper Bound</div>
              <div className="text-slate-200">{zopaResult.zopa_boundaries.upper_bound}</div>
            </div>
          </div>
          <div className="mt-4 p-4 bg-green-900/30 border border-green-700/50 rounded-lg">
            <div className="text-sm text-green-400 mb-1">Overlap Description</div>
            <div className="text-slate-200">{zopaResult.zopa_boundaries.overlap_description}</div>
          </div>
        </Card>
      )}
      {zopaResult.zopa_exists && !zopaResult.zopa_boundaries && (
        <Card
          padding="lg"
          className="border-amber-500/30 bg-amber-950/10 shadow-amber-900/20"
        >
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <AlertTriangle
              className="w-10 h-10 text-amber-400/80 mb-3"
              aria-hidden
            />
            <h3 className="text-lg font-semibold text-amber-100/95">Boundaries Unavailable</h3>
            <p className="text-sm text-slate-400 mt-2 max-w-md">
              A Zone of Possible Agreement appears to exist, but numeric boundaries could not be derived from the current inputs. Try adding clearer reservation prices or constraints, or re-run after more negotiation rounds.
            </p>
          </div>
        </Card>
      )}

      {/* Concession Recommendations */}
      {zopaResult.concession_recommendations.length > 0 && (
        <Card padding="lg">
          <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-amber-400" />
            Recommended Concessions
          </h3>
          <div className="space-y-3">
            {zopaResult.concession_recommendations.map((rec, index) => (
              <ConcessionCard key={`${rec.agent_id}-${index}`} recommendation={rec} />
            ))}
          </div>
        </Card>
      )}

      {/* Red Lines Summary */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">
          Red Lines (Non-Negotiables)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {zopaResult.positions.map((position) => (
            <div key={position.agent_id} className="p-4 bg-slate-700/50 rounded-lg">
              <div className="font-medium text-slate-200 mb-2">{position.agent_name}</div>
              {position.red_lines.length > 0 ? (
                <ul className="space-y-1">
                  {position.red_lines.map((line, idx) => (
                    <li key={idx} className="text-sm text-red-300 flex items-start gap-2">
                      <span className="text-red-400 mt-1">•</span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-slate-400">No explicit red lines identified</div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* BATNA Summary */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">
          BATNA (Best Alternatives)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {zopaResult.positions.map((position) => (
            <div key={position.agent_id} className="p-4 bg-slate-700/50 rounded-lg">
              <div className="font-medium text-slate-200 mb-2">{position.agent_name}</div>
              <div className="text-sm text-slate-300">
                {position.batna || 'No BATNA identified'}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// Position Bar Component
function PositionBar({
  position,
  getColor,
}: {
  position: AgentPosition;
  getColor: (flexibility: number) => string;
}) {
  const barWidth = position.flexibility_score * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-200">{position.agent_name}</span>
        <span className="text-sm text-slate-400">
          Flexibility: {(position.flexibility_score * 100).toFixed(0)}%
        </span>
      </div>
      <div className="relative h-8 bg-slate-700 rounded-lg overflow-hidden">
        {/* Flexibility Bar */}
        <div
          className={`absolute left-0 top-0 h-full ${getColor(position.flexibility_score)} transition-all duration-500`}
          style={{ width: `${barWidth}%` }}
        />
        {/* Red Line Markers */}
        {position.red_lines.map((_, idx) => (
          <div
            key={idx}
            className="absolute top-0 h-full w-1 bg-red-500"
            style={{ left: `${Math.min(90, 20 + idx * 25)}%` }}
            title="Red Line"
          />
        ))}
        {/* Current Position Marker */}
        {position.current_position && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full border-2 border-slate-900"
            style={{ left: `${barWidth - 3}%` }}
            title={`Current: ${position.current_position}`}
          />
        )}
      </div>
      {position.current_position && (
        <div className="text-xs text-slate-400 truncate">
          Current: {position.current_position}
        </div>
      )}
    </div>
  );
}

// Concession Card Component
function ConcessionCard({ recommendation }: { recommendation: ConcessionRecommendation }) {
  const impactWidth = recommendation.impact_score * 100;

  return (
    <div className="p-4 bg-slate-700/50 rounded-lg">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-medium text-slate-200">{recommendation.agent_name}</div>
          <div className="text-sm text-amber-300 mt-1">{recommendation.concession}</div>
          {recommendation.description && (
            <div className="text-xs text-slate-400 mt-2">{recommendation.description}</div>
          )}
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400 mb-1">Impact</div>
          <div className="w-16 h-2 bg-slate-600 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 rounded-full"
              style={{ width: `${impactWidth}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
