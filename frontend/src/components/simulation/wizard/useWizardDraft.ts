'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  normalizeSimulationEnvironmentType,
  type SimulationEnvironmentId,
} from '@/lib/environment-types';
import { INLINE_MONTE_CARLO_MAX_ITERATIONS, type ObjectiveMode } from './types';

const DRAFT_KEY = 'simulation_draft';

function clampMonteCarloIterations(value: number): number {
  return Math.min(
    INLINE_MONTE_CARLO_MAX_ITERATIONS,
    Math.max(10, value),
  );
}

/** Normalize iterations when Monte Carlo is turned on (incl. drafts stored below 10). */
export function normalizeMonteCarloIterationsOnEnable(value: number): number {
  return clampMonteCarloIterations(value);
}

export { clampMonteCarloIterations };

/** Read draft JSON; returns null on missing data or storage denial. */
export function readSimulationDraftRaw(): string | null {
  try {
    return localStorage.getItem(DRAFT_KEY);
  } catch (err) {
    console.error('Failed to read simulation draft from localStorage.', err);
    return null;
  }
}

/** Persist draft JSON; ignores quota / denial so the wizard stays usable in memory. */
export function writeSimulationDraftRaw(value: string): void {
  try {
    localStorage.setItem(DRAFT_KEY, value);
  } catch (err) {
    console.error('Failed to save simulation draft to localStorage.', err);
  }
}

/** Drop a corrupt or unwanted draft; ignores storage denial. */
export function clearSimulationDraftRaw(): void {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch (err) {
    console.error('Failed to clear simulation draft from localStorage.', err);
  }
}

/** Draft-persisted wizard fields + localStorage load/save. */
export function useWizardDraft() {
  const [simulationName, setSimulationName] = useState('');
  const [rounds, setRounds] = useState(10);
  const [environmentType, setEnvironmentType] =
    useState<SimulationEnvironmentId>('boardroom');
  const [modelSelection, setModelSelection] = useState('');
  const [monteCarloIterations, setMonteCarloIterationsState] = useState(20);
  const [monteCarloEnabled, setMonteCarloEnabledState] = useState(false);
  const [includePostRunReport, setIncludePostRunReport] = useState(true);
  const [includePostRunAnalytics, setIncludePostRunAnalytics] = useState(true);
  const [extendedSeedContext, setExtendedSeedContext] = useState(false);
  const [simulationObjective, setSimulationObjective] = useState('');
  const [objectiveMode, setObjectiveMode] = useState<ObjectiveMode>('consulting');

  /** Keep iterations in the same [10, cap] range the Monte Carlo Slider displays. */
  const setMonteCarloIterations = useCallback(
    (value: number | ((prev: number) => number)) => {
      setMonteCarloIterationsState((prev) =>
        clampMonteCarloIterations(typeof value === 'function' ? value(prev) : value),
      );
    },
    [],
  );

  /** Enabling MC persists a normalized iteration count into state (drafts below 10 → 10). */
  const setMonteCarloEnabled = useCallback((enabled: boolean) => {
    setMonteCarloEnabledState(enabled);
    if (enabled) {
      setMonteCarloIterationsState((prev) =>
        normalizeMonteCarloIterationsOnEnable(prev),
      );
    }
  }, []);

  // Hydrate from localStorage after mount (SSR-safe).
  useEffect(() => {
    const draft = readSimulationDraftRaw();
    if (!draft || draft === '{}') return;

    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>;
      /* eslint-disable react-hooks/set-state-in-effect -- one-shot localStorage hydrate */
      if (typeof parsed.simulationName === 'string' && parsed.simulationName) {
        setSimulationName(parsed.simulationName);
      }
      if (typeof parsed.rounds === 'number' && parsed.rounds) {
        setRounds(parsed.rounds);
      }
      if (typeof parsed.environmentType === 'string' && parsed.environmentType) {
        setEnvironmentType(
          normalizeSimulationEnvironmentType(parsed.environmentType)
        );
      }
      if (typeof parsed.modelSelection === 'string' && parsed.modelSelection) {
        setModelSelection(parsed.modelSelection);
      }
      if (typeof parsed.monteCarloEnabled === 'boolean') {
        setMonteCarloEnabledState(parsed.monteCarloEnabled);
      }
      if (typeof parsed.monteCarloIterations === 'number') {
        // Preserve below-10 draft values while MC is off; clamp when already enabled.
        if (parsed.monteCarloEnabled === true) {
          setMonteCarloIterationsState(
            clampMonteCarloIterations(parsed.monteCarloIterations),
          );
        } else {
          setMonteCarloIterationsState(parsed.monteCarloIterations);
        }
      }
      if (typeof parsed.includePostRunReport === 'boolean') {
        setIncludePostRunReport(parsed.includePostRunReport);
      }
      if (typeof parsed.includePostRunAnalytics === 'boolean') {
        setIncludePostRunAnalytics(parsed.includePostRunAnalytics);
      }
      if (typeof parsed.extendedSeedContext === 'boolean') {
        setExtendedSeedContext(parsed.extendedSeedContext);
      }
      if (typeof parsed.simulationObjective === 'string') {
        setSimulationObjective(parsed.simulationObjective);
      }
      if (
        parsed.objectiveMode === 'consulting' ||
        parsed.objectiveMode === 'general_prediction'
      ) {
        setObjectiveMode(parsed.objectiveMode);
      }
      /* eslint-enable react-hooks/set-state-in-effect */
    } catch (err) {
      console.error('Failed to parse simulation draft from localStorage.', err, {
        draftLength: typeof draft === 'string' ? draft.length : 0,
      });
      clearSimulationDraftRaw();
    }
  }, []);

  useEffect(() => {
    const draft = {
      simulationName,
      rounds,
      environmentType,
      modelSelection,
      monteCarloEnabled,
      monteCarloIterations,
      includePostRunReport,
      includePostRunAnalytics,
      extendedSeedContext,
      simulationObjective,
      objectiveMode,
    };

    const timeoutId = window.setTimeout(() => {
      writeSimulationDraftRaw(JSON.stringify(draft));
    }, 400);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    simulationName,
    rounds,
    environmentType,
    modelSelection,
    monteCarloEnabled,
    monteCarloIterations,
    includePostRunReport,
    includePostRunAnalytics,
    extendedSeedContext,
    simulationObjective,
    objectiveMode,
  ]);

  return {
    simulationName,
    setSimulationName,
    rounds,
    setRounds,
    environmentType,
    setEnvironmentType,
    modelSelection,
    setModelSelection,
    monteCarloIterations,
    setMonteCarloIterations,
    monteCarloEnabled,
    setMonteCarloEnabled,
    includePostRunReport,
    setIncludePostRunReport,
    includePostRunAnalytics,
    setIncludePostRunAnalytics,
    extendedSeedContext,
    setExtendedSeedContext,
    simulationObjective,
    setSimulationObjective,
    objectiveMode,
    setObjectiveMode,
  };
}
