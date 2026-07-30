'use client';

import { AlertCircle, Loader2, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { simulationEnvironmentLabel } from '@/lib/environment-types';
import type { Playbook, SimulationCostEstimate } from '@/lib/types';
import type { SimulationEnvironmentId } from '@/lib/environment-types';

export interface ReviewLaunchProps {
  selectedPlaybook: Playbook;
  staleSavedModelId: boolean;
  setModelSelection: (id: string) => void;
  simulationName: string;
  simulationObjective: string;
  enrichResearch: boolean;
  evidencePackCount: number;
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
  estimateFailed: boolean;
  costEstimate: SimulationCostEstimate | null;
  wizardLlmProvider: string;
  onEditStep: (stepIndex: number) => void;
}

function EditLink({
  stepIndex,
  label,
  onEditStep,
}: {
  stepIndex: number;
  label: string;
  onEditStep: (stepIndex: number) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onEditStep(stepIndex)}
      className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
    >
      <Pencil className="w-3 h-3" aria-hidden />
      {label}
    </button>
  );
}

export function ReviewLaunch({
  selectedPlaybook,
  staleSavedModelId,
  setModelSelection,
  simulationName,
  simulationObjective,
  enrichResearch,
  evidencePackCount,
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
  estimateFailed,
  costEstimate,
  wizardLlmProvider,
  onEditStep,
}: ReviewLaunchProps) {
  const objectiveSummary = simulationObjective.trim()
    ? simulationObjective.trim()
    : 'None';

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
                <strong>Provider default</strong>. Go back to Engine Settings to choose a model,
                or clear now.
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
          <div className="flex items-center justify-between gap-2 mb-3">
            <h4 className="text-sm font-medium text-foreground-subtle uppercase tracking-wider">
              Configuration Summary
            </h4>
            <EditLink stepIndex={3} label="Edit objective" onEditStep={onEditStep} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-foreground-muted">Name</p>
              <p className="text-foreground">{simulationName}</p>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-foreground-muted">Playbook</p>
                <EditLink stepIndex={0} label="Edit" onEditStep={onEditStep} />
              </div>
              <p className="text-foreground">{selectedPlaybook.name}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm text-foreground-muted">Objective</p>
              <p className="text-foreground text-sm line-clamp-3">{objectiveSummary}</p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Live research</p>
              <p className="text-foreground">
                {enrichResearch
                  ? evidencePackCount > 0
                    ? `On (${evidencePackCount} pack${evidencePackCount === 1 ? '' : 's'})`
                    : 'On (not prefetched)'
                  : 'Off'}
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-foreground-muted">Seed Documents</p>
                <EditLink stepIndex={2} label="Edit" onEditStep={onEditStep} />
              </div>
              <p className="text-foreground">
                {selectedSeedIds.length > 0
                  ? `${selectedSeedIds.length} attached`
                  : 'None'}
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-foreground-muted">Rounds</p>
                <EditLink stepIndex={4} label="Edit engine" onEditStep={onEditStep} />
              </div>
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
          <div className="flex items-center justify-between gap-2 mb-3">
            <h4 className="text-sm font-medium text-foreground-subtle uppercase tracking-wider">
              Agent Roster
            </h4>
            <EditLink stepIndex={1} label="Edit agents" onEditStep={onEditStep} />
          </div>
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

        <div className="p-4 bg-accent/10 rounded-lg border border-accent/30 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <p className="text-sm text-foreground-muted">Estimated cost (API)</p>
              <p className="text-2xl font-bold text-accent tabular-nums">
                {estimateLoading ? (
                  <span
                    className="inline-flex items-center gap-2 text-base text-foreground-muted"
                    role="status"
                    aria-live="polite"
                  >
                    <Loader2 className="w-5 h-5 animate-spin" aria-hidden />
                    <span className="sr-only">Estimating cost…</span>
                  </span>
                ) : costEstimate ? (
                  `~$${costEstimate.total_estimated_cost_usd.toFixed(2)}`
                ) : estimateFailed ? (
                  <span className="text-base text-foreground-muted">
                    Couldn&apos;t estimate cost
                  </span>
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
              ) : estimateFailed ? (
                <p className="text-foreground-muted">Couldn&apos;t estimate cost</p>
              ) : (
                <p className="text-foreground-muted">—</p>
              )}
              <p className="text-xs text-foreground-subtle mt-1">
                Playbook reference: {selectedPlaybook.typicalDuration}
              </p>
            </div>
          </div>

          {costEstimate && Object.keys(costEstimate.breakdown).length > 0 && (
            <div className="border-t border-border/60 pt-3">
              <p className="text-xs font-medium text-foreground-subtle uppercase tracking-wider mb-2">
                API cost breakdown
              </p>
              <ul className="space-y-1 text-xs text-foreground-muted">
                {Object.entries(costEstimate.breakdown).map(([key, item]) => (
                  <li key={key} className="flex justify-between gap-3">
                    <span>{item.description || key}</span>
                    <span className="tabular-nums shrink-0">
                      ~${item.cost_usd.toFixed(2)} ({item.tokens.toLocaleString()} tok)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {costEstimate && Object.keys(costEstimate.duration_breakdown).length > 0 && (
            <div className="border-t border-border/60 pt-3">
              <p className="text-xs font-medium text-foreground-subtle uppercase tracking-wider mb-2">
                Duration breakdown (minutes)
              </p>
              <ul className="space-y-1 text-xs text-foreground-muted">
                {Object.entries(costEstimate.duration_breakdown).map(([key, minutes]) => (
                  <li key={key} className="flex justify-between gap-3">
                    <span>{key.replace(/_/g, ' ')}</span>
                    <span className="tabular-nums shrink-0">{minutes.toFixed(1)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
