'use client';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import type { SimulationWizardState } from './useSimulationWizard';

export interface ObjectiveStepProps {
  w: SimulationWizardState;
}

export function ObjectiveStep({ w }: ObjectiveStepProps) {
  const {
    simulationName,
    setSimulationName,
    simulationObjective,
    setSimulationObjective,
    objectiveMode,
    setObjectiveMode,
    parseLoading,
    rosterLoading,
    ontologyLoading,
    selectedPlaybook,
    handleParseObjective,
    handleSuggestRoster,
    handleGenerateOntology,
    lastGeneratedOntology,
    setLastGeneratedOntology,
    parseObjectiveError,
    suggestRosterError,
    generateOntologyError,
    parsedObjective,
    enrichResearch,
    setEnrichResearch,
    setEvidencePacks,
    setResearchMessage,
    prefetchLoading,
    handlePrefetchResearch,
    researchMessage,
    evidencePacks,
  } = w;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Objective</h2>
        <p className="text-foreground-muted mt-1">
          Name your simulation and define what you want to learn
        </p>
      </div>
      <div className="space-y-6">
        <Input
          label="Simulation Name"
          value={simulationName}
          onChange={(e) => setSimulationName(e.target.value)}
          placeholder="Enter a name for your simulation"
          error={
            simulationName.trim().length > 50
              ? 'Name must be 50 characters or less'
              : undefined
          }
        />

        <div>
          <label
            htmlFor="simulation-objective"
            className="block text-sm font-medium text-foreground-muted mb-2"
          >
            Simulation objective (optional)
          </label>
          <textarea
            id="simulation-objective"
            className="w-full min-h-[100px] rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted"
            value={simulationObjective}
            onChange={(e) => setSimulationObjective(e.target.value)}
            placeholder="What you are testing, success metrics, key actors, hypotheses…"
          />
          <div className="mt-2">
            <details className="rounded-lg border border-border bg-background-secondary/30 p-3">
              <summary className="cursor-pointer text-sm font-medium text-foreground select-none">
                Advanced tools
              </summary>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <select
                  value={objectiveMode}
                  onChange={(e) =>
                    setObjectiveMode(
                      e.target.value === 'general_prediction'
                        ? 'general_prediction'
                        : 'consulting',
                    )
                  }
                  className="text-sm rounded-lg border border-border bg-background px-2 py-1.5 text-foreground"
                  aria-label="Objective mode"
                >
                  <option value="consulting">Consulting / war-game</option>
                  <option value="general_prediction">General prediction</option>
                </select>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleParseObjective()}
                  disabled={parseLoading || !simulationObjective.trim()}
                >
                  {parseLoading ? 'Parsing…' : 'Parse objective'}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleSuggestRoster()}
                  disabled={
                    rosterLoading || (!simulationObjective.trim() && !selectedPlaybook)
                  }
                >
                  {rosterLoading ? 'Suggesting…' : 'Suggest roster'}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleGenerateOntology()}
                  disabled={
                    ontologyLoading || (!simulationObjective.trim() && !selectedPlaybook)
                  }
                >
                  {ontologyLoading ? 'Mapping…' : 'Map key entities'}
                </Button>
                {lastGeneratedOntology ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setLastGeneratedOntology(null)}
                  >
                    Clear entity map
                  </Button>
                ) : null}
              </div>
              {parseObjectiveError ? (
                <p className="mt-1 text-xs text-red-400" role="alert">
                  {parseObjectiveError}
                </p>
              ) : null}
              {suggestRosterError ? (
                <p className="mt-1 text-xs text-red-400" role="alert">
                  {suggestRosterError}
                </p>
              ) : null}
              {generateOntologyError ? (
                <p className="mt-1 text-xs text-red-400" role="alert">
                  {generateOntologyError}
                </p>
              ) : null}
              {lastGeneratedOntology ? (
                <p className="mt-1 text-xs text-accent">
                  Entity map cached — the next &quot;Suggest roster&quot; will use it for
                  extraction.
                </p>
              ) : null}
              {parsedObjective?.summary != null && (
                <p className="mt-2 text-xs text-foreground-muted line-clamp-3">
                  Parsed: {String(parsedObjective.summary)}
                </p>
              )}
            </details>
          </div>
        </div>

        <label className="flex items-start gap-3 p-3 rounded-lg border border-border bg-background-secondary/40 cursor-pointer">
          <input
            type="checkbox"
            className="mt-1 w-4 h-4 rounded border-border-hover text-accent"
            checked={enrichResearch}
            onChange={(e) => {
              const on = e.target.checked;
              setEnrichResearch(on);
              if (!on) {
                setEvidencePacks([]);
                setResearchMessage('');
              }
            }}
          />
          <span>
            <span className="font-medium text-foreground text-sm">
              Enrich with live research
            </span>
            <span className="block text-xs text-foreground-muted mt-0.5">
              Prefetch evidence packs. Requires web research to be enabled by your
              administrator.
            </span>
          </span>
        </label>
        {enrichResearch && (
          <div className="space-y-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void handlePrefetchResearch()}
              disabled={prefetchLoading}
            >
              {prefetchLoading ? 'Fetching…' : 'Prefetch research'}
            </Button>
            {researchMessage ? (
              <p className="text-xs text-foreground-muted">{researchMessage}</p>
            ) : null}
            {Array.isArray(evidencePacks) && evidencePacks.length > 0 ? (
              <ul className="text-xs text-foreground-muted space-y-1 max-h-32 overflow-y-auto">
                {evidencePacks.map((p, i) => {
                  const name =
                    typeof p.entity_name === 'string' ? p.entity_name : 'entity';
                  const err = typeof p.error === 'string' ? p.error : undefined;
                  const citationCount = Array.isArray(p.citations)
                    ? p.citations.length
                    : 0;
                  return (
                    <li key={i}>
                      {name} — {err ?? `${citationCount} sources`}
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
