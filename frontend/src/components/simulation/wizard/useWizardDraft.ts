'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  normalizeSimulationEnvironmentType,
  type SimulationEnvironmentId,
} from '@/lib/environment-types';
import {
  INLINE_MONTE_CARLO_MAX_ITERATIONS,
  WIZARD_STEPS,
  type ObjectiveMode,
} from './types';
import {
  hasMeaningfulWizardDraft,
  parseSimulationDraftPayload,
  serializeSimulationDraftPayload,
  type SimulationDraftPayload,
} from './wizardDraftSchema';

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

function applyParameterFieldsFromDraft(
  parsed: SimulationDraftPayload,
  setters: {
    setSimulationName: (value: string) => void;
    setRounds: (value: number) => void;
    setEnvironmentType: (value: SimulationEnvironmentId) => void;
    setModelSelection: (value: string) => void;
    setMonteCarloEnabledState: (value: boolean) => void;
    setMonteCarloIterationsState: (value: number) => void;
    setIncludePostRunReport: (value: boolean) => void;
    setIncludePostRunAnalytics: (value: boolean) => void;
    setExtendedSeedContext: (value: boolean) => void;
    setSimulationObjective: (value: string) => void;
    setObjectiveMode: (value: ObjectiveMode) => void;
  },
): void {
  if (typeof parsed.simulationName === 'string' && parsed.simulationName) {
    setters.setSimulationName(parsed.simulationName);
  }
  if (typeof parsed.rounds === 'number' && parsed.rounds) {
    setters.setRounds(parsed.rounds);
  }
  if (typeof parsed.environmentType === 'string' && parsed.environmentType) {
    setters.setEnvironmentType(
      normalizeSimulationEnvironmentType(parsed.environmentType),
    );
  }
  if (typeof parsed.modelSelection === 'string' && parsed.modelSelection) {
    setters.setModelSelection(parsed.modelSelection);
  }
  if (typeof parsed.monteCarloEnabled === 'boolean') {
    setters.setMonteCarloEnabledState(parsed.monteCarloEnabled);
  }
  if (typeof parsed.monteCarloIterations === 'number') {
    if (parsed.monteCarloEnabled === true) {
      setters.setMonteCarloIterationsState(
        clampMonteCarloIterations(parsed.monteCarloIterations),
      );
    } else {
      setters.setMonteCarloIterationsState(parsed.monteCarloIterations);
    }
  }
  if (typeof parsed.includePostRunReport === 'boolean') {
    setters.setIncludePostRunReport(parsed.includePostRunReport);
  }
  if (typeof parsed.includePostRunAnalytics === 'boolean') {
    setters.setIncludePostRunAnalytics(parsed.includePostRunAnalytics);
  }
  if (typeof parsed.extendedSeedContext === 'boolean') {
    setters.setExtendedSeedContext(parsed.extendedSeedContext);
  }
  if (typeof parsed.simulationObjective === 'string') {
    setters.setSimulationObjective(parsed.simulationObjective);
  }
  if (
    parsed.objectiveMode === 'consulting' ||
    parsed.objectiveMode === 'general_prediction'
  ) {
    setters.setObjectiveMode(parsed.objectiveMode);
  }
}

function resetParameterDefaults(setters: {
  setSimulationName: (value: string) => void;
  setRounds: (value: number) => void;
  setEnvironmentType: (value: SimulationEnvironmentId) => void;
  setModelSelection: (value: string) => void;
  setMonteCarloEnabledState: (value: boolean) => void;
  setMonteCarloIterationsState: (value: number) => void;
  setIncludePostRunReport: (value: boolean) => void;
  setIncludePostRunAnalytics: (value: boolean) => void;
  setExtendedSeedContext: (value: boolean) => void;
  setSimulationObjective: (value: string) => void;
  setObjectiveMode: (value: ObjectiveMode) => void;
}): void {
  setters.setSimulationName('');
  setters.setRounds(10);
  setters.setEnvironmentType('boardroom');
  setters.setModelSelection('');
  setters.setMonteCarloEnabledState(false);
  setters.setMonteCarloIterationsState(20);
  setters.setIncludePostRunReport(true);
  setters.setIncludePostRunAnalytics(true);
  setters.setExtendedSeedContext(false);
  setters.setSimulationObjective('');
  setters.setObjectiveMode('consulting');
}

/** Draft-persisted wizard fields + localStorage load/save. */
export function useWizardDraft(playbookId?: string | null) {
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
  const [currentStep, setCurrentStepState] = useState(0);
  const [agentConfigs, setAgentConfigs] = useState<Record<string, number>>({});
  const [selectedSeedIds, setSelectedSeedIds] = useState<string[]>([]);
  const [pendingPlaybookId, setPendingPlaybookId] = useState<string | null>(null);
  const [showDraftBanner, setShowDraftBanner] = useState(false);
  const pendingDraftRef = useRef<SimulationDraftPayload | null>(null);
  const parametersHydratedRef = useRef(false);

  const parameterSetters = {
    setSimulationName,
    setRounds,
    setEnvironmentType,
    setModelSelection,
    setMonteCarloEnabledState,
    setMonteCarloIterationsState,
    setIncludePostRunReport,
    setIncludePostRunAnalytics,
    setExtendedSeedContext,
    setSimulationObjective,
    setObjectiveMode,
  };

  const setCurrentStep = useCallback((step: number) => {
    setCurrentStepState(
      Math.min(Math.max(0, step), WIZARD_STEPS.length - 1),
    );
  }, []);

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

  const applyNavigationFields = useCallback((parsed: SimulationDraftPayload) => {
    if (typeof parsed.currentStep === 'number') {
      setCurrentStep(parsed.currentStep);
    }
    if (parsed.agentConfigs && typeof parsed.agentConfigs === 'object') {
      setAgentConfigs(parsed.agentConfigs);
    }
    if (Array.isArray(parsed.selectedSeedIds)) {
      setSelectedSeedIds(parsed.selectedSeedIds);
    }
    if (typeof parsed.playbookId === 'string' && parsed.playbookId) {
      setPendingPlaybookId(parsed.playbookId);
    }
  }, [setCurrentStep]);

  // Hydrate parameters from localStorage after mount (SSR-safe).
  useEffect(() => {
    const raw = readSimulationDraftRaw();
    const parsed = parseSimulationDraftPayload(raw);

    if (parsed && hasMeaningfulWizardDraft(parsed)) {
      pendingDraftRef.current = parsed;
      setShowDraftBanner(true);
      applyParameterFieldsFromDraft(parsed, parameterSetters);
    } else if (parsed) {
      applyParameterFieldsFromDraft(parsed, parameterSetters);
    } else if (raw) {
      clearSimulationDraftRaw();
    }

    parametersHydratedRef.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot hydrate
  }, []);

  const resumeDraft = useCallback(() => {
    const parsed = pendingDraftRef.current;
    if (!parsed) {
      setShowDraftBanner(false);
      return;
    }
    applyParameterFieldsFromDraft(parsed, parameterSetters);
    applyNavigationFields(parsed);
    setShowDraftBanner(false);
  }, [applyNavigationFields]);

  const discardDraft = useCallback(() => {
    clearSimulationDraftRaw();
    pendingDraftRef.current = null;
    setShowDraftBanner(false);
    setCurrentStep(0);
    setAgentConfigs({});
    setSelectedSeedIds([]);
    setPendingPlaybookId(null);
    resetParameterDefaults(parameterSetters);
  }, [setCurrentStep]);

  useEffect(() => {
    if (!parametersHydratedRef.current) return;

    const draft: SimulationDraftPayload = {
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
      currentStep,
      agentConfigs,
      selectedSeedIds,
      ...(playbookId ? { playbookId } : {}),
    };

    const timeoutId = window.setTimeout(() => {
      writeSimulationDraftRaw(serializeSimulationDraftPayload(draft));
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
    currentStep,
    agentConfigs,
    selectedSeedIds,
    playbookId,
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
    currentStep,
    setCurrentStep,
    agentConfigs,
    setAgentConfigs,
    selectedSeedIds,
    setSelectedSeedIds,
    pendingPlaybookId,
    setPendingPlaybookId,
    showDraftBanner,
    resumeDraft,
    discardDraft,
  };
}
