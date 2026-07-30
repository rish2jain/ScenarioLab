'use client';

import { useState, useEffect } from 'react';
import {
  normalizeSimulationEnvironmentType,
  type SimulationEnvironmentId,
} from '@/lib/environment-types';
import { INLINE_MONTE_CARLO_MAX_ITERATIONS, type ObjectiveMode } from './types';

const DRAFT_KEY = 'simulation_draft';

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
  const [monteCarloIterations, setMonteCarloIterations] = useState(20);
  const [monteCarloEnabled, setMonteCarloEnabled] = useState(false);
  const [includePostRunReport, setIncludePostRunReport] = useState(true);
  const [includePostRunAnalytics, setIncludePostRunAnalytics] = useState(true);
  const [extendedSeedContext, setExtendedSeedContext] = useState(false);
  const [simulationObjective, setSimulationObjective] = useState('');
  const [objectiveMode, setObjectiveMode] = useState<ObjectiveMode>('consulting');

  /** Keep draft/state in the same [10, cap] range the Monte Carlo Slider displays. */
  useEffect(() => {
    if (!monteCarloEnabled) return;
    const normalized = Math.min(
      INLINE_MONTE_CARLO_MAX_ITERATIONS,
      Math.max(10, monteCarloIterations),
    );
    if (normalized !== monteCarloIterations) {
      setMonteCarloIterations(normalized);
    }
  }, [monteCarloEnabled, monteCarloIterations]);

  useEffect(() => {
    const draft = readSimulationDraftRaw();
    if (!draft || draft === '{}') return;

    try {
      const parsed = JSON.parse(draft);
      if (parsed.simulationName) setSimulationName(parsed.simulationName);
      if (parsed.rounds) setRounds(parsed.rounds);
      if (parsed.environmentType) {
        setEnvironmentType(
          normalizeSimulationEnvironmentType(parsed.environmentType)
        );
      }
      if (parsed.modelSelection) setModelSelection(parsed.modelSelection);
      if (typeof parsed.monteCarloEnabled === 'boolean') {
        setMonteCarloEnabled(parsed.monteCarloEnabled);
      }
      if (typeof parsed.monteCarloIterations === 'number') {
        setMonteCarloIterations(
          Math.min(
            INLINE_MONTE_CARLO_MAX_ITERATIONS,
            Math.max(10, parsed.monteCarloIterations),
          ),
        );
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
