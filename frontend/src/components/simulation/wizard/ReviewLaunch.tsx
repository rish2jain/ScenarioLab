'use client';

import { AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { simulationEnvironmentLabel } from '@/lib/environment-types';
import type { Playbook, SimulationCostEstimate } from '@/lib/types';
import type { SimulationEnvironmentId } from '@/lib/environment-types';

export interface ReviewLaunchProps {
  selectedPlaybook: Playbook;
  staleSavedModelId: boolean;
  setModelSelection: (id: string) => void;
  simulationName: string;
  rounds: number;
  environmentType: SimulationEnvironmentId;
  modelSelectionLabel: string;
  totalAgents: number;
  selectedSeedIds: string[];
  effectiveMonteCarloIterations: number;
  includePostRunReport: boolean;
  includePostRunAnalytics: boolean;
  extendedSeedContext: boolean;
  agentConfigs: Record<string, number>;
  estimateLoading: boolean;
  costEstimate: SimulationCostEstimate | null;
  wizardLlmProvider: string;
}

export function ReviewLaunch({
  selectedPlaybook,
  staleSavedModelId,
  setModelSelection,
  simulationName,
  rounds,
  environmentType,
  modelSelectionLabel,
  totalAgents,
  selectedSeedIds,
  effectiveMonteCarloIterations,
  includePostRunReport,
  includePostRunAnalytics,
  extendedSeedContext,
  agentConfigs,
  estimateLoading,
  costEstimate,
  wizardLlmProvider,
}: ReviewLaunchProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Review & Launch</h2>
        <p className="text-foreground-muted mt-1">
          Review your simulation configuration before launching
        </p>
      </div>
      <div className="space-y-4">
        {staleSavedModelId ? (
          <div
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-foreground"
            role="status"
          >
            <p className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <span>
                Invalid saved model for this server — the launch request will use{' '}
                <strong>Provider default</strong>. Go back to Set Parameters to choose a model, or
                clear now.
              </span>
            </p>
            <Button
              type="button"
              variant="secondary"
              className="shrink-0"
              onClick={() => setModelSelection('')}
            >
              Use provider default
            </Button>
          </div>
        ) : null}
        <div className="p-4 bg-background-secondary/50 rounded-lg border border-border">
          <h4 className="text-sm font-medium text-foreground-subtle uppercase tracking-wider mb-3">
            Configuration Summary
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-foreground-muted">Name</p>
              <p className="text-foreground">{simulationName}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Playbook</p>
              <p className="text-foreground">{selectedPlaybook.name}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Rounds</p>
              <p className="text-foreground">{rounds}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Environment</p>
              <p className="text-foreground">{simulationEnvironmentLabel(environmentType)}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Model</p>
              <p className="text-foreground">{modelSelectionLabel}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Total Agents</p>
              <p className="text-foreground">{totalAgents}</p>
            </div>
            {selectedSeedIds.length > 0 && (
              <div>
                <p className="text-sm text-foreground-muted">Seed Documents</p>
                <p className="text-foreground">{selectedSeedIds.length} attached</p>
              </div>
            )}
            <div>
              <p className="text-sm text-foreground-muted">Monte Carlo</p>
              <p className="text-foreground">
                {effectiveMonteCarloIterations > 1
                  ? `${effectiveMonteCarloIterations} iterations`
                  : 'Off'}
              </p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Post-run report</p>
              <p className="text-foreground">{includePostRunReport ? 'On' : 'Off'}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Post-run analytics</p>
              <p className="text-foreground">{includePostRunAnalytics ? 'On' : 'Off'}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Extended seed context</p>
              <p className="text-foreground">
                {extendedSeedContext && selectedSeedIds.length > 0 ? 'On' : 'Off'}
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 bg-background-secondary/50 rounded-lg border border-border">
          <h4 className="text-sm font-medium text-foreground-subtle uppercase tracking-wider mb-3">
            Agent Roster
          </h4>
          <div className="space-y-2">
            {Object.entries(agentConfigs)
              .filter(([, count]) => count > 0)
              .map(([role, count]) => (
                <div key={role} className="flex items-center justify-between">
                  <span className="text-foreground-muted">{role}</span>
                  <span className="text-foreground font-medium">x{count}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="p-4 bg-accent/10 rounded-lg border border-accent/30">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <p className="text-sm text-foreground-muted">Estimated cost (API)</p>
              <p className="text-2xl font-bold text-accent tabular-nums">
                {estimateLoading ? (
                  <span className="inline-flex items-center gap-2 text-base text-foreground-muted">
                    <Loader2 className="w-5 h-5 animate-spin" />
                  </span>
                ) : costEstimate ? (
                  `~$${costEstimate.total_estimated_cost_usd.toFixed(2)}`
                ) : (
                  '—'
                )}
              </p>
              {costEstimate && (
                <>
                  <p className="text-xs text-foreground-muted mt-1">
                    ~{costEstimate.total_estimated_tokens.toLocaleString()} tokens
                  </p>
                  {wizardLlmProvider ? (
                    <p className="text-xs text-foreground-muted mt-1">
                      Priced for server LLM: {wizardLlmProvider}
                    </p>
                  ) : null}
                </>
              )}
            </div>
            <div className="text-left sm:text-right">
              <p className="text-sm text-foreground-muted">Estimated duration</p>
              {costEstimate ? (
                <p className="text-foreground font-medium">
                  {costEstimate.estimated_duration_min_minutes.toFixed(0)}–
                  {costEstimate.estimated_duration_max_minutes.toFixed(0)} min (wall-clock)
                </p>
              ) : (
                <p className="text-foreground-muted">—</p>
              )}
              <p className="text-xs text-foreground-subtle mt-1">
                Playbook reference: {selectedPlaybook.typicalDuration}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
