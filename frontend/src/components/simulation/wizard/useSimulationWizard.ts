'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/ui/Toast';
import { usePlaybookStore, useSimulationStore, useUploadStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { SimulationCostEstimate } from '@/lib/types';
import { randomUUIDCompat } from '@/lib/randomUUID';
import {
  filterValidSeedIds,
  resolveExtendedSeedContext,
} from './seedIds';
import {
  INLINE_MONTE_CARLO_MAX_ITERATIONS,
  WIZARD_STEPS,
  type CreateSimulationRequest,
} from './types';
import { useWizardDraft } from './useWizardDraft';
import { useWizardModels } from './useWizardModels';
import { usePlaybookDetail } from './usePlaybookDetail';
import { useObjectiveTools } from './useObjectiveTools';
import {
  applyAgentCountDelta,
  canProceedFromReason,
  getCanProceedReason,
} from './wizardProgress';

export function useSimulationWizard() {
  const router = useRouter();
  const { addToast } = useToast();
  const { playbooks, setPlaybooks, selectedPlaybook, setSelectedPlaybook } = usePlaybookStore();
  const addSimulation = useSimulationStore((state) => state.addSimulation);
  const { files: uploadedFiles, addFile, updateFile, mergeSeedsFromApi } =
    useUploadStore();

  const [isLoading, setIsLoading] = useState(false);
  const [costEstimate, setCostEstimate] = useState<SimulationCostEstimate | null>(null);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [estimateFailed, setEstimateFailed] = useState(false);
  const [hybridAvailable, setHybridAvailable] = useState(false);
  const [hybridLocalEnabled, setHybridLocalEnabled] = useState(false);
  const [maxVisitedStep, setMaxVisitedStep] = useState(0);

  const draft = useWizardDraft(selectedPlaybook?.id ?? null);
  const {
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
  } = draft;

  const {
    wizardLlmModels,
    wizardLlmProvider,
    effectiveModelSelection,
    staleSavedModelId,
    modelSelectionLabel,
  } = useWizardModels(modelSelection, setModelSelection);

  const { playbookDetailLoading, playbookDetailError, retryPlaybookDetail } =
    usePlaybookDetail({
      selectedPlaybook,
      setSelectedPlaybook,
      setSimulationName,
      setAgentConfigs,
      agentConfigs,
    });

  const {
    parsedObjective,
    enrichResearch,
    setEnrichResearch,
    evidencePacks,
    setEvidencePacks,
    researchMessage,
    setResearchMessage,
    prefetchLoading,
    parseLoading,
    rosterLoading,
    lastGeneratedOntology,
    setLastGeneratedOntology,
    ontologyLoading,
    parseObjectiveError,
    suggestRosterError,
    generateOntologyError,
    handleParseObjective,
    handleSuggestRoster,
    handleGenerateOntology,
    handlePrefetchResearch,
  } = useObjectiveTools({
    simulationObjective,
    objectiveMode,
    selectedPlaybook,
    setAgentConfigs,
    uploadedFiles,
    selectedSeedIds,
    simulationName,
  });

  const effectiveMonteCarloIterations = useMemo(() => {
    if (!monteCarloEnabled || rounds < 10) return 1;
    return Math.min(
      INLINE_MONTE_CARLO_MAX_ITERATIONS,
      Math.max(10, monteCarloIterations),
    );
  }, [monteCarloEnabled, monteCarloIterations, rounds]);

  useEffect(() => {
    setMaxVisitedStep((prev) => Math.max(prev, currentStep));
  }, [currentStep]);

  useEffect(() => {
    if (!pendingPlaybookId || playbooks.length === 0) return;
    const playbook = playbooks.find((p) => p.id === pendingPlaybookId);
    if (playbook) {
      setSelectedPlaybook(playbook);
      setPendingPlaybookId(null);
    }
  }, [pendingPlaybookId, playbooks, setSelectedPlaybook, setPendingPlaybookId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const cap = await api.getInferenceCapabilities();
        if (cancelled) return;
        setHybridAvailable(cap.hybridAvailable);
        if (cap.hybridAvailable && cap.defaultInferenceMode === 'hybrid') {
          setHybridLocalEnabled(true);
        }
      } catch {
        if (!cancelled) setHybridAvailable(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const seeds = await api.listSeeds();
        if (!cancelled && seeds.length > 0) mergeSeedsFromApi(seeds);
      } catch {
        /* offline or backend unavailable */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mergeSeedsFromApi]);

  useEffect(() => {
    const loadPlaybooks = async () => {
      try {
        const data = await api.getPlaybooks();
        setPlaybooks(data);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Could not load playbooks.';
        addToast(message, 'error');
      }
    };
    void loadPlaybooks();
  }, [setPlaybooks, addToast]);

  const canProceedReason = useMemo(
    () =>
      getCanProceedReason({
        currentStep,
        selectedPlaybook,
        playbookDetailLoading,
        agentConfigs,
        simulationName,
      }),
    [
      currentStep,
      selectedPlaybook,
      playbookDetailLoading,
      agentConfigs,
      simulationName,
    ],
  );

  const canProceed = useCallback(
    () => canProceedFromReason(canProceedReason),
    [canProceedReason],
  );

  const handleNext = () => {
    if (!canProceed()) return;
    if (currentStep < WIZARD_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleStartOver = () => {
    discardDraft();
    setSelectedPlaybook(null);
    setMaxVisitedStep(0);
  };

  const validSeedIds = useMemo(
    () => filterValidSeedIds(selectedSeedIds, uploadedFiles),
    [selectedSeedIds, uploadedFiles],
  );

  const handleLaunch = async () => {
    if (!selectedPlaybook) return;

    setIsLoading(true);

    try {
      const payload: CreateSimulationRequest = {
        name: simulationName,
        playbookId: selectedPlaybook.id,
        playbookName: selectedPlaybook.name,
        status: 'pending',
        seedIds: validSeedIds,
        agentConfigs,
        playbook: selectedPlaybook,
        config: {
          rounds,
          environmentType,
          modelSelection: effectiveModelSelection,
          monteCarloIterations: effectiveMonteCarloIterations,
          monteCarloEnabled,
          includePostRunReport,
          includePostRunAnalytics,
          extendedSeedContext: resolveExtendedSeedContext(
            extendedSeedContext,
            validSeedIds
          ),
          ...(hybridAvailable && hybridLocalEnabled
            ? { hybridLocalEnabled: true }
            : {}),
        },
        currentRound: 0,
        totalRounds: rounds,
        agents: [],
        ...(simulationObjective.trim()
          ? { simulationRequirement: simulationObjective.trim() }
          : {}),
        objectiveMode,
        ...(parsedObjective ? { parsedObjective } : {}),
        ...(enrichResearch && evidencePacks.length > 0
          ? { preflightEvidencePacks: evidencePacks }
          : {}),
      };
      const newSimulation = await api.createSimulation(payload);

      localStorage.removeItem('simulation_draft');
      addSimulation(newSimulation);

      try {
        await api.controlSimulation(newSimulation.id, 'start');
      } catch (startErr) {
        console.error('Failed to auto-start simulation:', startErr);
        addToast(
          startErr instanceof Error
            ? `Simulation created, but could not start: ${startErr.message}`
            : 'Simulation created, but could not start automatically. Press Start on the monitor.',
          'error'
        );
      }

      router.push(`/simulations/${newSimulation.id}`);
    } catch (error) {
      console.error('Failed to create simulation:', error);
      const msg =
        error instanceof Error
          ? error.message
          : typeof error === 'string'
            ? error
            : 'Could not create simulation.';
      addToast(msg, 'error');
      const lower = msg.toLowerCase();
      if (
        lower.includes('model') &&
        (lower.includes('provider') ||
          lower.includes('default') ||
          lower.includes('cloud api') ||
          lower.includes('does not match'))
      ) {
        setModelSelection('');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const updateAgentCount = (role: string, delta: number) => {
    setAgentConfigs((prev) =>
      applyAgentCountDelta(prev, role, delta, selectedPlaybook?.roster),
    );
  };

  const totalAgents = Object.values(agentConfigs).reduce((a, b) => a + b, 0);

  useEffect(() => {
    if (totalAgents < 1) {
      setCostEstimate(null);
      setEstimateFailed(false);
      return;
    }

    const handle = window.setTimeout(() => {
      void (async () => {
        setEstimateLoading(true);
        setEstimateFailed(false);
        try {
          const est = await api.estimateSimulationCost({
            agent_count: totalAgents,
            rounds,
            monte_carlo_iterations: effectiveMonteCarloIterations,
            include_post_run_report: includePostRunReport,
            include_post_run_analytics: includePostRunAnalytics,
            extended_seed_context: resolveExtendedSeedContext(
              extendedSeedContext,
              validSeedIds
            ),
          });
          setCostEstimate(est);
          setEstimateFailed(est === null);
        } catch {
          setCostEstimate(null);
          setEstimateFailed(true);
        } finally {
          setEstimateLoading(false);
        }
      })();
    }, 400);

    return () => window.clearTimeout(handle);
  }, [
    totalAgents,
    rounds,
    effectiveMonteCarloIterations,
    includePostRunReport,
    includePostRunAnalytics,
    extendedSeedContext,
    validSeedIds,
  ]);

  const toggleSeedId = (id: string) => {
    setSelectedSeedIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    );
  };

  const handleFilesDrop = async (files: File[]) => {
    for (const file of files) {
      let tempId: string | undefined;
      try {
        tempId = `local-seed-${randomUUIDCompat()}`;
        const uploadTempId = tempId;
        addFile({
          id: uploadTempId,
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'uploading',
          progress: 0,
          uploadedAt: new Date().toISOString(),
        });

        const uploaded = await api.uploadFile(file, {
          onProgress: (progress) => {
            updateFile(uploadTempId, { progress });
          },
          clientUploadId: uploadTempId,
        });
        updateFile(uploadTempId, { ...uploaded });
        setSelectedSeedIds((prev) =>
          prev.includes(uploaded.id) ? prev : [...prev, uploaded.id]
        );
      } catch (error) {
        console.error('Failed to upload seed file:', error);
        const msg = error instanceof Error ? error.message : 'Upload failed';
        if (tempId) {
          updateFile(tempId, {
            status: 'error',
            errorMessage: msg,
          });
        } else {
          addToast(msg, 'error');
        }
      }
    }
  };

  const handleResumeDraft = () => {
    resumeDraft();
  };

  return {
    steps: WIZARD_STEPS,
    currentStep,
    setCurrentStep,
    maxVisitedStep,
    playbooks,
    selectedPlaybook,
    setSelectedPlaybook,
    playbookDetailLoading,
    playbookDetailError,
    retryPlaybookDetail,
    agentConfigs,
    updateAgentCount,
    totalAgents,
    uploadedFiles,
    selectedSeedIds,
    toggleSeedId,
    handleFilesDrop,
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
    costEstimate,
    estimateLoading,
    estimateFailed,
    wizardLlmModels,
    wizardLlmProvider,
    simulationObjective,
    setSimulationObjective,
    objectiveMode,
    setObjectiveMode,
    parsedObjective,
    enrichResearch,
    setEnrichResearch,
    evidencePacks,
    setEvidencePacks,
    researchMessage,
    setResearchMessage,
    prefetchLoading,
    parseLoading,
    rosterLoading,
    lastGeneratedOntology,
    setLastGeneratedOntology,
    ontologyLoading,
    parseObjectiveError,
    suggestRosterError,
    generateOntologyError,
    hybridAvailable,
    hybridLocalEnabled,
    setHybridLocalEnabled,
    effectiveMonteCarloIterations,
    staleSavedModelId,
    modelSelectionLabel,
    handleParseObjective,
    handleSuggestRoster,
    handleGenerateOntology,
    handlePrefetchResearch,
    handleNext,
    handleBack,
    handleLaunch,
    canProceed,
    canProceedReason,
    isLoading,
    showDraftBanner,
    resumeDraft: handleResumeDraft,
    discardDraft: handleStartOver,
  };
}

export type SimulationWizardState = ReturnType<typeof useSimulationWizard>;
