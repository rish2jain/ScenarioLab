'use client';

import { useMemo, useRef, type KeyboardEvent } from 'react';
import { AlertCircle, Clock, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Slider } from '@/components/ui/Slider';
import { SIMULATION_ENVIRONMENTS } from '@/lib/environment-types';
import { INLINE_MONTE_CARLO_MAX_ITERATIONS } from './types';
import { nextRadioIndex, rovingTabIndex } from './radioGroupNav';
import { mergeWizardModelOptions } from './wizardModelOptions';
import type { SimulationWizardState } from './useSimulationWizard';

export interface EngineSettingsProps {
  w: SimulationWizardState;
}

export function EngineSettings({ w }: EngineSettingsProps) {
  const {
    hybridAvailable,
    hybridLocalEnabled,
    setHybridLocalEnabled,
    rounds,
    setRounds,
    environmentType,
    setEnvironmentType,
    wizardLlmProvider,
    wizardLlmModels,
    modelSelection,
    setModelSelection,
    staleSavedModelId,
    includePostRunReport,
    setIncludePostRunReport,
    includePostRunAnalytics,
    setIncludePostRunAnalytics,
    extendedSeedContext,
    setExtendedSeedContext,
    selectedSeedIds,
    monteCarloEnabled,
    setMonteCarloEnabled,
    monteCarloIterations,
    setMonteCarloIterations,
    estimateLoading,
    estimateFailed,
    costEstimate,
  } = w;

  const environmentGroupRef = useRef<HTMLDivElement>(null);
  const modelGroupRef = useRef<HTMLDivElement>(null);

  const environmentValues = SIMULATION_ENVIRONMENTS.map((env) => env.value);
  const environmentTabValue = environmentValues.includes(environmentType)
    ? environmentType
    : environmentValues[0]!;

  const modelOptions = useMemo(
    () => mergeWizardModelOptions(wizardLlmModels),
    [wizardLlmModels],
  );
  const modelValues = modelOptions.map((m) => m.id);
  const modelTabValue = modelValues.includes(modelSelection) ? modelSelection : '';

  const focusRadioAt = (group: HTMLDivElement | null, index: number) => {
    const radios = group?.querySelectorAll<HTMLElement>('[role="radio"]');
    radios?.[index]?.focus();
  };

  const onEnvironmentKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const current = environmentValues.indexOf(environmentTabValue);
    const next = nextRadioIndex(event.key, current, environmentValues.length);
    if (next === null) return;
    event.preventDefault();
    setEnvironmentType(environmentValues[next]!);
    focusRadioAt(environmentGroupRef.current, next);
  };

  const onModelKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const current = modelValues.indexOf(modelTabValue);
    const next = nextRadioIndex(event.key, current, modelValues.length);
    if (next === null) return;
    event.preventDefault();
    setModelSelection(modelValues[next]!);
    focusRadioAt(modelGroupRef.current, next);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Engine Settings</h2>
        <p className="text-foreground-muted mt-1">
          Configure rounds, environment, model, and optional features
        </p>
      </div>
      <div className="space-y-6">
        {hybridAvailable && (
          <div className="p-4 rounded-lg border border-border bg-background-secondary/20">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="mt-1 w-4 h-4 rounded border-border-hover text-accent focus:ring-accent"
                checked={hybridLocalEnabled}
                onChange={(e) => setHybridLocalEnabled(e.target.checked)}
              />
              <div>
                <span className="font-medium text-foreground">
                  Use local hardware for faster simulation
                </span>
                <p className="text-sm text-foreground-muted mt-1">
                  Round 1 uses your cloud provider for quality calibration. Subsequent
                  rounds run locally.
                </p>
              </div>
            </label>
          </div>
        )}

        <Slider
          label="Number of Rounds"
          min={5}
          max={50}
          value={rounds}
          onChange={setRounds}
        />

        <div>
          <span
            id="environment-type-label"
            className="block text-sm font-medium text-foreground-muted mb-2"
          >
            Environment Type
          </span>
          <div
            ref={environmentGroupRef}
            role="radiogroup"
            aria-labelledby="environment-type-label"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"
            onKeyDown={onEnvironmentKeyDown}
          >
            {SIMULATION_ENVIRONMENTS.map((env) => (
              <button
                key={env.value}
                type="button"
                role="radio"
                aria-checked={environmentType === env.value}
                tabIndex={rovingTabIndex(environmentTabValue === env.value)}
                onClick={() => setEnvironmentType(env.value)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  environmentType === env.value
                    ? 'border-accent bg-accent/10 text-accent'
                    : 'border-border bg-background-secondary/50 text-foreground-muted hover:border-border-hover'
                }`}
              >
                <span className="block text-sm font-medium text-foreground">{env.label}</span>
                <span className="block text-xs mt-1 text-foreground-muted leading-snug">
                  {env.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <span
            id="model-selection-label"
            className="block text-sm font-medium text-foreground-muted mb-2"
          >
            Model Selection (Optional)
          </span>
          {wizardLlmProvider ? (
            <p className="text-xs text-foreground-muted mb-2">
              Choose which AI model runs your agents (
              <span className="text-foreground">{wizardLlmProvider}</span>
              {modelOptions.length <= 1 ? ' — only the recommended model applies' : ''}
              ).
            </p>
          ) : null}
          <div
            ref={modelGroupRef}
            role="radiogroup"
            aria-labelledby="model-selection-label"
            className={`grid gap-3 ${
              modelOptions.length <= 1
                ? 'grid-cols-1 sm:grid-cols-1'
                : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
            }`}
            onKeyDown={onModelKeyDown}
          >
            {modelOptions.map((model) => (
              <button
                key={model.id === '' ? '__provider_default__' : model.id}
                type="button"
                role="radio"
                aria-checked={modelSelection === model.id}
                tabIndex={rovingTabIndex(modelTabValue === model.id)}
                onClick={() => setModelSelection(model.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  modelSelection === model.id
                    ? 'border-accent bg-accent/10'
                    : 'border-border bg-background-secondary/50 hover:border-border-hover'
                }`}
              >
                <div className="font-medium text-foreground">{model.name}</div>
                <div className="text-xs text-foreground-muted">{model.desc}</div>
              </button>
            ))}
          </div>
          {staleSavedModelId ? (
            <div
              className="mt-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-foreground"
              role="status"
            >
              <p className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <span>
                  A saved model id from a previous session does not match this server&apos;s LLM
                  provider. Launch will use <strong>Provider default</strong> until you pick a
                  valid model or clear this.
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
        </div>

        <div className="border border-border rounded-lg p-4 space-y-3 bg-background-secondary/20">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent flex-shrink-0" />
            <h3 className="text-sm font-semibold text-foreground">Simulation features</h3>
          </div>
          <p className="text-xs text-foreground-muted">
            Toggle optional work to balance quality, runtime, and API cost. Estimates update
            automatically.
          </p>

          <label className="flex items-start gap-3 p-3 rounded-lg border border-border bg-background-secondary/40 cursor-pointer hover:border-border-hover">
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 rounded border-border-hover text-accent focus:ring-accent"
              checked={includePostRunReport}
              onChange={(e) => setIncludePostRunReport(e.target.checked)}
            />
            <span>
              <span className="font-medium text-foreground text-sm">Post-run report</span>
              <span className="block text-xs text-foreground-muted mt-0.5">
                Generate a narrative report after the simulation completes (extra tokens and ~1
                min)
              </span>
            </span>
          </label>

          <label className="flex items-start gap-3 p-3 rounded-lg border border-border bg-background-secondary/40 cursor-pointer hover:border-border-hover">
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 rounded border-border-hover text-accent focus:ring-accent"
              checked={includePostRunAnalytics}
              onChange={(e) => setIncludePostRunAnalytics(e.target.checked)}
            />
            <span>
              <span className="font-medium text-foreground text-sm">Post-run analytics</span>
              <span className="block text-xs text-foreground-muted mt-0.5">
                Run analytics over outcomes after completion (extra tokens and ~40 s)
              </span>
            </span>
          </label>

          <label
            className={`flex items-start gap-3 p-3 rounded-lg border border-border bg-background-secondary/40 cursor-pointer hover:border-border-hover ${
              selectedSeedIds.length === 0 ? 'opacity-60' : ''
            }`}
          >
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 rounded border-border-hover text-accent focus:ring-accent"
              checked={extendedSeedContext && selectedSeedIds.length > 0}
              disabled={selectedSeedIds.length === 0}
              onChange={(e) => setExtendedSeedContext(e.target.checked)}
            />
            <span>
              <span className="font-medium text-foreground text-sm">Extended seed context</span>
              <span className="block text-xs text-foreground-muted mt-0.5">
                Injects more characters from each seed document into agent prompts (backend cap
                100k chars per file vs 24k).
                {selectedSeedIds.length === 0
                  ? ' Select documents in the previous step to enable.'
                  : ` ${selectedSeedIds.length} document(s) selected.`}
              </span>
            </span>
          </label>

          <div className="pt-2 border-t border-border space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-foreground">Monte Carlo runs</span>
              {rounds < 10 && (
                <span className="text-xs text-amber-400">Requires 10+ rounds</span>
              )}
            </div>
            {rounds >= 10 ? (
              <>
                <label className="flex items-start gap-3 p-3 rounded-lg border border-border bg-background-secondary/40 cursor-pointer hover:border-border-hover">
                  <input
                    type="checkbox"
                    className="mt-1 w-4 h-4 rounded border-border-hover text-accent focus:ring-accent"
                    checked={monteCarloEnabled}
                    onChange={(e) => setMonteCarloEnabled(e.target.checked)}
                  />
                  <span>
                    <span className="font-medium text-foreground text-sm">Enable Monte Carlo</span>
                    <span className="block text-xs text-foreground-muted mt-0.5">
                      After your main simulation finishes, the server runs additional sampled runs
                      (10–{INLINE_MONTE_CARLO_MAX_ITERATIONS}, server cap) and stores summary stats
                      under results. High token cost.
                    </span>
                  </span>
                </label>
                {monteCarloEnabled && (
                  <Slider
                    label="Monte Carlo iterations"
                    min={10}
                    max={INLINE_MONTE_CARLO_MAX_ITERATIONS}
                    step={1}
                    value={monteCarloIterations}
                    onChange={setMonteCarloIterations}
                    valueFormatter={(v) => `${v} runs`}
                  />
                )}
              </>
            ) : (
              <div className="flex items-center gap-2 p-3 rounded-lg border border-amber-500/20 bg-amber-500/5">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <p className="text-xs text-amber-200/90">
                  Increase rounds to at least 10 to enable Monte Carlo sampling.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 rounded-lg border border-accent/30 bg-accent/5 space-y-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                Estimated cost
              </p>
              <p className="text-2xl font-bold text-accent tabular-nums">
                {estimateLoading ? (
                  <span className="inline-flex items-center gap-2 text-foreground-muted text-base">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Calculating…
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
                    ~{costEstimate.total_estimated_tokens.toLocaleString()} tokens (rough)
                  </p>
                  {wizardLlmProvider ? (
                    <p className="text-xs text-foreground-muted mt-1">
                      Priced for server LLM: {wizardLlmProvider}
                    </p>
                  ) : null}
                </>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs font-medium text-foreground-subtle uppercase tracking-wider flex items-center justify-end gap-1">
                <Clock className="w-3.5 h-3.5" />
                Est. duration
              </p>
              {costEstimate ? (
                <p className="text-foreground font-medium">
                  {costEstimate.estimated_duration_min_minutes.toFixed(0)}–
                  {costEstimate.estimated_duration_max_minutes.toFixed(0)} min
                  <span className="text-foreground-muted text-sm font-normal">
                    {' '}
                    (typ. ~{costEstimate.estimated_duration_minutes.toFixed(0)} min)
                  </span>
                </p>
              ) : estimateLoading ? (
                <p className="text-foreground-muted text-sm">…</p>
              ) : estimateFailed ? (
                <p className="text-foreground-muted text-sm">Couldn&apos;t estimate cost</p>
              ) : (
                <p className="text-foreground-muted text-sm">—</p>
              )}
            </div>
          </div>
          {costEstimate && costEstimate.optimization_suggestions.length > 0 && (
            <ul className="text-xs text-foreground-muted space-y-1 list-disc list-inside border-t border-border/60 pt-3">
              {costEstimate.optimization_suggestions.slice(0, 3).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
