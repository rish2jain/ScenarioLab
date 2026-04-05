'use client';

import { Suspense, useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Building2,
  ShieldAlert,
  Swords,
  Users,
  ChevronLeft,
  ChevronRight,
  Check,
  Plus,
  Minus,
  AlertCircle,
  FileText,
  Loader2,
  Clock,
  Sparkles,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StepWizard } from '@/components/ui/StepWizard';
import { Slider } from '@/components/ui/Slider';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { DropZone } from '@/components/ui/DropZone';
import { useToast } from '@/components/ui/Toast';
import { usePlaybookStore, useSimulationStore, useUploadStore } from '@/lib/store';
import { api } from '@/lib/api';
import {
  SIMULATION_ENVIRONMENTS,
  normalizeSimulationEnvironmentType,
  simulationEnvironmentLabel,
  type SimulationEnvironmentId,
} from '@/lib/environment-types';
import type { Playbook, Agent, SimulationCostEstimate, WizardModelOption } from '@/lib/types';

/** Must match backend `Settings.inline_monte_carlo_max_iterations` (default 25). */
const INLINE_MONTE_CARLO_MAX_ITERATIONS = 25;

/** Shape passed to api.createSimulation from this page. */
interface CreateSimulationRequest {
  name: string;
  playbookId: string;
  playbookName: string;
  status: 'pending';
  seedIds: string[];
  agentConfigs: Record<string, number>;
  playbook: Playbook;
  config: {
    rounds: number;
    environmentType: string;
    modelSelection?: string;
    monteCarloIterations: number;
    monteCarloEnabled: boolean;
    includePostRunReport: boolean;
    includePostRunAnalytics: boolean;
    extendedSeedContext: boolean;
    hybridLocalEnabled?: boolean;
  };
  currentRound: number;
  totalRounds: number;
  agents: Agent[];
  simulationRequirement?: string;
  objectiveMode?: 'consulting' | 'general_prediction';
  parsedObjective?: Record<string, unknown>;
  preflightEvidencePacks?: Record<string, unknown>[];
}

const steps = [
  { id: 'playbook', label: 'Select Playbook' },
  { id: 'agents', label: 'Configure Agents' },
  { id: 'documents', label: 'Seed Documents' },
  { id: 'parameters', label: 'Set Parameters' },
  { id: 'review', label: 'Review & Launch' },
];

const iconMap: Record<string, React.ReactNode> = {
  Building2: <Building2 className="w-8 h-8" />,
  ShieldAlert: <ShieldAlert className="w-8 h-8" />,
  Swords: <Swords className="w-8 h-8" />,
  Users: <Users className="w-8 h-8" />,
};

/** Applies `?playbook=<id>` from the URL to the playbook store when playbooks load. */
function PlaybookFromQuerySync({
  playbooks,
  setSelectedPlaybook,
}: {
  playbooks: Playbook[];
  setSelectedPlaybook: (p: Playbook) => void;
}) {
  const searchParams = useSearchParams();
  useEffect(() => {
    const id = searchParams.get('playbook');
    if (!id || playbooks.length === 0) return;
    const match = playbooks.find((p) => p.id === id);
    if (match) setSelectedPlaybook(match);
  }, [searchParams, playbooks, setSelectedPlaybook]);
  return null;
}

export default function NewSimulationPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const { playbooks, setPlaybooks, selectedPlaybook, setSelectedPlaybook } = usePlaybookStore();
  const addSimulation = useSimulationStore((state) => state.addSimulation);
  const { files: uploadedFiles, addFile, updateFile, mergeSeedsFromApi } =
    useUploadStore();

  const [currentStep, setCurrentStep] = useState(0);
  const [selectedSeedIds, setSelectedSeedIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
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
  const [costEstimate, setCostEstimate] = useState<SimulationCostEstimate | null>(null);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [wizardLlmModels, setWizardLlmModels] = useState<WizardModelOption[]>([]);
  const [wizardLlmProvider, setWizardLlmProvider] = useState<string>('');
  const [agentConfigs, setAgentConfigs] = useState<Record<string, number>>({});
  /** True while lazy-loading full playbook (roster) after selection — blocks Next on step 0. */
  const [playbookDetailLoading, setPlaybookDetailLoading] = useState(false);
  /** Set when detail fetch fails so the user sees why Next stays disabled; cleared on retry/success. */
  const [playbookDetailError, setPlaybookDetailError] = useState<string | null>(null);
  /** Increment to re-run the detail fetch for the same selection (Retry). */
  const [playbookDetailRetryToken, setPlaybookDetailRetryToken] = useState(0);
  const [simulationObjective, setSimulationObjective] = useState('');
  const [objectiveMode, setObjectiveMode] = useState<'consulting' | 'general_prediction'>(
    'consulting'
  );
  const [parsedObjective, setParsedObjective] = useState<Record<string, unknown> | null>(
    null
  );
  const [enrichResearch, setEnrichResearch] = useState(false);
  const [evidencePacks, setEvidencePacks] = useState<Record<string, unknown>[]>([]);
  const [researchMessage, setResearchMessage] = useState('');
  const [prefetchLoading, setPrefetchLoading] = useState(false);
  const [parseLoading, setParseLoading] = useState(false);
  const [rosterLoading, setRosterLoading] = useState(false);
  const [lastGeneratedOntology, setLastGeneratedOntology] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [ontologyLoading, setOntologyLoading] = useState(false);
  const [parseObjectiveError, setParseObjectiveError] = useState('');
  const [suggestRosterError, setSuggestRosterError] = useState('');
  const [generateOntologyError, setGenerateOntologyError] = useState('');
  const [hybridAvailable, setHybridAvailable] = useState(false);
  const [hybridLocalEnabled, setHybridLocalEnabled] = useState(false);

  const effectiveMonteCarloIterations = useMemo(() => {
    if (!monteCarloEnabled || rounds < 10) return 1;
    return Math.min(
      INLINE_MONTE_CARLO_MAX_ITERATIONS,
      Math.max(1, monteCarloIterations),
    );
  }, [monteCarloEnabled, monteCarloIterations, rounds]);

  /** Changes only when id+name pairs change (not only `uploadedFiles` reference). */
  const uploadedFilesIdNameKey = useMemo(
    () => uploadedFiles.map((f) => `${f.id}:${f.name}`).sort().join('|'),
    [uploadedFiles],
  );

  const fileIdToName = useMemo(() => {
    const m: Record<string, string> = {};
    for (const f of uploadedFiles) {
      m[f.id] = f.name;
    }
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key captures id+name; `uploadedFiles` read when key changes
  }, [uploadedFilesIdNameKey]);

  /** JSON array string so value is stable when only unrelated uploads change (not array identity). */
  const seedLabels = useMemo(
    () =>
      JSON.stringify(
        selectedSeedIds.map((id) => `${id}:${fileIdToName[id] ?? ''}`).sort(),
      ),
    [selectedSeedIds, fileIdToName],
  );

  /** Same inputs as `handlePrefetchResearch` seed texts; if these drift, cached packs are invalid. */
  const researchPrefetchFingerprint = useMemo(() => {
    const objective = simulationObjective.trim();
    return JSON.stringify({
      objective,
      seedLabels: JSON.parse(seedLabels) as string[],
      simName: simulationName.trim(),
    });
  }, [seedLabels, simulationObjective, simulationName]);

  useEffect(() => {
    setEvidencePacks([]);
    setResearchMessage('');
  }, [researchPrefetchFingerprint]);

  /** Clear structured parse when the objective text no longer matches ``raw_text`` (avoids stale payloads). */
  useEffect(() => {
    const t = simulationObjective.trim();
    if (!parsedObjective) return;
    const raw =
      typeof parsedObjective.raw_text === 'string' ? parsedObjective.raw_text.trim() : '';
    if (raw !== t) {
      setParsedObjective(null);
    }
  }, [simulationObjective, parsedObjective]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await api.getWizardModels();
        if (cancelled || !data) return;
        setWizardLlmProvider(data.provider);
        setWizardLlmModels(data.models);
      } catch (err) {
        if (cancelled) return;
        console.error('getWizardModels failed', err);
        addToast(
          err instanceof Error ? err.message : 'Could not load model list for the wizard.',
          'error',
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [addToast]);

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

  // Drop stale wizard picks when the server has no curated list (local/Ollama) or the id
  // is not in the current vendor list — e.g. draft had gpt-4o but server is now Ollama.
  useEffect(() => {
    if (wizardLlmModels.length === 0) {
      if (wizardLlmProvider === '') return;
      if (modelSelection) setModelSelection('');
      return;
    }
    const ids = new Set(wizardLlmModels.map((m) => m.id));
    if (modelSelection && !ids.has(modelSelection)) {
      setModelSelection('');
    }
  }, [wizardLlmModels, modelSelection, wizardLlmProvider]);

  /** Value actually sent to the API — never a stale id from localStorage after a provider switch. */
  const effectiveModelSelection = useMemo(() => {
    const t = modelSelection.trim();
    if (!t) return '';
    if (!wizardLlmProvider) return '';
    if (wizardLlmModels.length === 0) return '';
    return wizardLlmModels.some((m) => m.id === t) ? t : '';
  }, [modelSelection, wizardLlmProvider, wizardLlmModels]);

  const staleSavedModelId = useMemo(
    () =>
      Boolean(
        modelSelection.trim() &&
          wizardLlmProvider &&
          effectiveModelSelection !== modelSelection.trim()
      ),
    [modelSelection, wizardLlmProvider, effectiveModelSelection]
  );

  const modelSelectionLabel = useMemo(() => {
    if (!effectiveModelSelection.trim()) return 'Provider default';
    const m = wizardLlmModels.find((x) => x.id === effectiveModelSelection);
    return m ? `${m.name} (${effectiveModelSelection})` : effectiveModelSelection;
  }, [effectiveModelSelection, wizardLlmModels]);

  useEffect(() => {
    const draft = localStorage.getItem('simulation_draft');

    try {
      if (draft && draft !== '{}') {
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
      }
    } catch (err) {
      console.error('Failed to parse simulation draft from localStorage.', err, {
        draftLength: typeof draft === 'string' ? draft.length : 0,
      });
      localStorage.removeItem('simulation_draft');
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
      localStorage.setItem('simulation_draft', JSON.stringify(draft));
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

  const handleParseObjective = async () => {
    const text = simulationObjective.trim();
    if (!text) return;
    setParseObjectiveError('');
    setParseLoading(true);
    try {
      const p = await api.parseSimulationObjective(text, objectiveMode);
      setParsedObjective(p);
    } catch (err) {
      console.error('parseSimulationObjective failed', err);
      const detail =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'Unknown error';
      const msg = `Could not parse objective: ${detail}`;
      setParseObjectiveError(msg);
      addToast(msg, 'error');
    } finally {
      setParseLoading(false);
    }
  };

  const handleSuggestRoster = async () => {
    const text =
      simulationObjective.trim() ||
      `Playbook: ${selectedPlaybook?.name ?? ''}. Standard consulting war-game.`;
    setSuggestRosterError('');
    setRosterLoading(true);
    try {
      const s = await api.suggestSimulationRoster(
        text,
        selectedPlaybook?.id ?? null,
        lastGeneratedOntology
      );
      if (!s || typeof s !== 'object') return;
      const ac = s.agent_configs as Record<string, number> | undefined;
      if (ac && typeof ac === 'object') {
        setAgentConfigs((prev) => ({ ...prev, ...ac }));
      }
    } catch (err) {
      console.error('suggestSimulationRoster failed', err);
      const detail =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'Unknown error';
      const msg = `Could not suggest roster: ${detail}`;
      setSuggestRosterError(msg);
      addToast(msg, 'error');
    } finally {
      setRosterLoading(false);
    }
  };

  const handleGenerateOntology = async () => {
    const excerpt =
      simulationObjective.trim() ||
      `Playbook: ${selectedPlaybook?.name ?? ''}. Standard consulting war-game.`;
    setGenerateOntologyError('');
    setOntologyLoading(true);
    try {
      const o = await api.generateSimulationOntology({
        document_excerpt: excerpt.slice(0, 12000),
        simulation_requirement: simulationObjective.trim(),
        mode: objectiveMode,
      });
      setLastGeneratedOntology(o);
    } catch (err) {
      console.error('generateSimulationOntology failed', err);
      const detail =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'Unknown error';
      const msg = `Could not generate ontology: ${detail}`;
      setGenerateOntologyError(msg);
      addToast(msg, 'error');
    } finally {
      setOntologyLoading(false);
    }
  };

  const handlePrefetchResearch = async () => {
    setPrefetchLoading(true);
    setResearchMessage('');
    try {
      const seedTexts: string[] = [];
      if (simulationObjective.trim()) seedTexts.push(simulationObjective.trim());
      selectedSeedIds.forEach((id) => {
        const f = uploadedFiles.find((x) => x.id === id);
        if (f?.name) seedTexts.push(`Document: ${f.name}`);
      });
      if (seedTexts.length === 0) seedTexts.push(simulationName || 'simulation');
      const res = await api.preflightResearch({
        seed_texts: seedTexts,
        simulation_requirement: simulationObjective.trim(),
        max_entities: 6,
      });
      if (res) {
        setResearchMessage(res.message);
        setEvidencePacks(res.evidence_packs ?? []);
      }
    } catch (err) {
      console.error('preflightResearch failed', err);
      const detail =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'Unknown error';
      const msg = `Research preflight failed: ${detail}`;
      setResearchMessage(msg);
      addToast(msg, 'error');
    } finally {
      setPrefetchLoading(false);
    }
  };

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

  useEffect(() => {
    if (!selectedPlaybook) {
      setPlaybookDetailLoading(false);
      setPlaybookDetailError(null);
      return;
    }

    let cancelled = false;
    const targetId = selectedPlaybook.id;

    const loadAndConfigure = async () => {
      const needsRosterFetch =
        !selectedPlaybook.roster || selectedPlaybook.roster.length === 0;
      if (needsRosterFetch) {
        setPlaybookDetailLoading(true);
      }
      setPlaybookDetailError(null);
      try {
        let playbook = selectedPlaybook;
        if (needsRosterFetch) {
          const full = await api.getPlaybook(targetId);
          if (cancelled) return;
          if (full === null) {
            const msg =
              'Playbook details could not be loaded. It may have been removed or unavailable.';
            setPlaybookDetailError(msg);
            addToast(msg, 'error');
            return;
          }
          setSelectedPlaybook(full);
          playbook = full;
        }

        if (cancelled) return;

        const roster = playbook.roster ?? [];
        const configs: Record<string, number> = {};
        roster.forEach((role) => {
          configs[role.role] = role.defaultCount;
        });
        setAgentConfigs(configs);
        setSimulationName((prev) =>
          prev ? prev : `${playbook.name} - ${new Date().toLocaleDateString()}`
        );
      } catch (err) {
        if (cancelled) return;
        console.error('getPlaybook failed', err);
        const msg =
          err instanceof Error
            ? err.message
            : 'Could not load playbook details.';
        setPlaybookDetailError(msg);
        addToast(msg, 'error');
      } finally {
        if (!cancelled) {
          setPlaybookDetailLoading(false);
        }
      }
    };

    void loadAndConfigure();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable setters/addToast omitted; deps are playbook + retry only
  }, [selectedPlaybook, playbookDetailRetryToken]);

  const handleNext = () => {
    if (!canProceed()) return;
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleLaunch = async () => {
    if (!selectedPlaybook) return;

    setIsLoading(true);

    const validSeedIds = selectedSeedIds.filter((id) =>
      uploadedFiles.some(
        (f) =>
          f.id === id &&
          (f.status === 'completed' || f.status === 'processing')
      )
    );

    try {
      const payload: CreateSimulationRequest = {
        name: simulationName,
        playbookId: selectedPlaybook.id,
        playbookName: selectedPlaybook.name,
        status: 'pending',
        seedIds: validSeedIds,
        // Pass extra fields so api.createSimulation can build the backend body
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
          extendedSeedContext: extendedSeedContext && selectedSeedIds.length > 0,
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
    setAgentConfigs((prev) => ({
      ...prev,
      [role]: Math.max(0, (prev[role] || 0) + delta),
    }));
  };

  const totalAgents = Object.values(agentConfigs).reduce((a, b) => a + b, 0);

  useEffect(() => {
    if (totalAgents < 1) {
      setCostEstimate(null);
      return;
    }

    const handle = window.setTimeout(() => {
      void (async () => {
        setEstimateLoading(true);
        try {
          const est = await api.estimateSimulationCost({
            agent_count: totalAgents,
            rounds,
            monte_carlo_iterations: effectiveMonteCarloIterations,
            include_post_run_report: includePostRunReport,
            include_post_run_analytics: includePostRunAnalytics,
            extended_seed_context: extendedSeedContext && selectedSeedIds.length > 0,
          });
          setCostEstimate(est);
        } catch {
          setCostEstimate(null);
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
    selectedSeedIds.length,
  ]);

  const toggleSeedId = (id: string) => {
    setSelectedSeedIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    );
  };

  const handleFilesDrop = async (files: File[]) => {
    for (const file of files) {
      const tempId = `local-seed-${crypto.randomUUID()}`;
      addFile({
        id: tempId,
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'uploading',
        progress: 0,
        uploadedAt: new Date().toISOString(),
      });

      try {
        const uploaded = await api.uploadFile(file, {
          onProgress: (progress) => {
            updateFile(tempId, { progress });
          },
          clientUploadId: tempId,
        });
        updateFile(tempId, { ...uploaded });
        setSelectedSeedIds((prev) => [...prev, uploaded.id]);
      } catch (error) {
        console.error('Failed to upload seed file:', error);
        updateFile(tempId, {
          status: 'error',
          errorMessage: 'Upload failed',
        });
      }
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return (
          !!selectedPlaybook &&
          !playbookDetailLoading &&
          (selectedPlaybook.roster?.length ?? 0) > 0
        );
      case 1:
        return totalAgents > 0;
      case 2:
        return true; // Documents step is optional
      case 3:
        return simulationName.trim().length > 0 && simulationName.trim().length <= 50;
      default:
        return true;
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 animate-fade-in max-w-5xl mx-auto">
      <Suspense fallback={null}>
        <PlaybookFromQuerySync playbooks={playbooks} setSelectedPlaybook={setSelectedPlaybook} />
      </Suspense>
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">New Simulation</h1>
        <p className="text-foreground-muted mt-1 text-sm sm:text-base">
          Configure your war-gaming scenario step by step
        </p>
      </div>

      {/* Step Wizard */}
      <Card padding="lg">
        <StepWizard steps={steps} currentStep={currentStep} />
      </Card>

      {/* Step Content */}
      <Card padding="lg">
        {currentStep === 0 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-foreground">
              Select a Playbook
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {playbooks.map((playbook) => (
                <button
                  key={playbook.id}
                  type="button"
                  onClick={() => setSelectedPlaybook(playbook)}
                  className={`p-6 rounded-lg border-2 text-left transition-all ${
                    selectedPlaybook?.id === playbook.id
                      ? 'border-accent bg-accent/10'
                      : 'border-border hover:border-border-hover bg-background-secondary/50'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                        selectedPlaybook?.id === playbook.id
                          ? 'bg-accent/20 text-accent'
                          : 'bg-background-tertiary text-foreground-muted'
                      }`}
                    >
                      {iconMap[playbook.icon] || <Building2 className="w-8 h-8" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-foreground">
                          {playbook.name}
                        </h3>
                        <Badge size="sm">{playbook.category}</Badge>
                      </div>
                      <p className="text-sm text-foreground-muted mt-1">
                        {playbook.description}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-foreground-subtle">
                        <span>{playbook.typicalDuration}</span>
                        <span>•</span>
                        <span>{playbook.agentCount} agents</span>
                        <span>•</span>
                        <span>{playbook.rounds} rounds</span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            {selectedPlaybook && playbookDetailLoading && (
              <div
                className="flex items-center gap-3 text-sm text-foreground-muted"
                role="status"
                aria-live="polite"
              >
                <Loader2
                  className="w-4 h-4 animate-spin text-accent flex-shrink-0"
                  aria-hidden
                />
                <span>Loading playbook roster…</span>
              </div>
            )}
            {selectedPlaybook && playbookDetailError && !playbookDetailLoading && (
              <div
                className="flex flex-col gap-3 rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-sm text-foreground"
                role="alert"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle
                    className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5"
                    aria-hidden
                  />
                  <p>{playbookDetailError}</p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  className="self-start"
                  onClick={() => setPlaybookDetailRetryToken((t) => t + 1)}
                >
                  Retry loading playbook
                </Button>
              </div>
            )}
          </div>
        )}

        {currentStep === 1 && selectedPlaybook && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Configure Agents
              </h2>
              <p className="text-foreground-muted mt-1">
                Adjust the number of agents for each role in your simulation
              </p>
            </div>
            <div className="space-y-4">
              {(selectedPlaybook.roster ?? []).map((role) => (
                <div
                  key={role.role}
                  className="flex items-center justify-between p-4 bg-background-secondary/50 rounded-lg border border-border"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-foreground">{role.role}</h4>
                      {role.required && (
                        <Badge variant="info" size="sm">Required</Badge>
                      )}
                    </div>
                    <p className="text-sm text-foreground-muted mt-1">
                      {role.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="default" size="sm">
                        {role.archetype}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => updateAgentCount(role.role, -1)}
                      disabled={agentConfigs[role.role] <= 0}
                      className="w-8 h-8 rounded-lg bg-background-tertiary flex items-center justify-center text-foreground-muted hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-8 text-center font-medium text-foreground">
                      {agentConfigs[role.role] || 0}
                    </span>
                    <button
                      onClick={() => updateAgentCount(role.role, 1)}
                      className="w-8 h-8 rounded-lg bg-background-tertiary flex items-center justify-center text-foreground-muted hover:bg-border"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-background-secondary/30 rounded-lg border border-border">
              <div className="flex items-center justify-between">
                <span className="text-foreground-muted">Total Agents</span>
                <span className="text-xl font-semibold text-foreground">
                  {totalAgents}
                </span>
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Seed Documents
              </h2>
              <p className="text-foreground-muted mt-1">
                Attach documents that agents will reference during the simulation
              </p>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-foreground-muted">
                  Previously Uploaded Files
                </h3>
                {uploadedFiles.some((f) => f.status === 'processing') && (
                  <p className="text-xs text-foreground-muted">
                    If graph extraction stays on &quot;processing&quot;,{' '}
                    <Link
                      href="/upload"
                      className="text-accent underline hover:no-underline"
                    >
                      Upload
                    </Link>{' '}
                    → Process Seeds re-queues extraction.
                  </p>
                )}
                {uploadedFiles.map((file) => {
                  const canSelect =
                    file.status === 'completed' || file.status === 'processing';
                  return (
                  <label
                    key={file.id}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                      !canSelect
                        ? 'border-border bg-background-secondary/30 cursor-not-allowed opacity-70'
                        : selectedSeedIds.includes(file.id)
                        ? 'border-accent bg-accent/10 cursor-pointer'
                        : 'border-border bg-background-secondary/50 hover:border-border-hover cursor-pointer'
                    }`}
                  >
                    <input
                      type="checkbox"
                      disabled={!canSelect}
                      checked={selectedSeedIds.includes(file.id)}
                      onChange={() => canSelect && toggleSeedId(file.id)}
                      className="w-4 h-4 rounded border-border-hover text-accent focus:ring-accent disabled:opacity-50"
                    />
                    <FileText className="w-5 h-5 text-foreground-muted flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-foreground-muted">
                        {file.size < 1024 * 1024
                          ? (file.size / 1024).toFixed(1) + ' KB'
                          : (file.size / (1024 * 1024)).toFixed(1) + ' MB'}
                      </p>
                    </div>
                  </label>
                  );
                })}
              </div>
            )}

            <div>
              <h3 className="text-sm font-medium text-foreground-muted mb-2">
                Upload New Files
              </h3>
              <DropZone onFilesDrop={handleFilesDrop} />
            </div>

            <div className="p-4 bg-background-secondary/30 rounded-lg border border-border">
              <div className="flex items-center justify-between">
                <span className="text-foreground-muted">Selected Documents</span>
                <span className="text-xl font-semibold text-foreground">
                  {selectedSeedIds.length}
                </span>
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Set Parameters
              </h2>
              <p className="text-foreground-muted mt-1">
                Configure the simulation behavior and model settings
              </p>
            </div>
            <div className="space-y-6">
              <Input
                label="Simulation Name"
                value={simulationName}
                onChange={(e) => setSimulationName(e.target.value)}
                placeholder="Enter a name for your simulation"
                error={simulationName.trim().length > 50 ? 'Name must be 50 characters or less' : undefined}
              />

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

              <div>
                <label className="block text-sm font-medium text-foreground-muted mb-2">
                  Simulation objective (optional)
                </label>
                <textarea
                  className="w-full min-h-[100px] rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted"
                  value={simulationObjective}
                  onChange={(e) => setSimulationObjective(e.target.value)}
                  placeholder="What you are testing, success metrics, key actors, hypotheses…"
                />
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <select
                    value={objectiveMode}
                    onChange={(e) =>
                      setObjectiveMode(
                        e.target.value === 'general_prediction'
                          ? 'general_prediction'
                          : 'consulting'
                      )
                    }
                    className="text-sm rounded-lg border border-border bg-background px-2 py-1.5 text-foreground"
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
                    disabled={rosterLoading || (!simulationObjective.trim() && !selectedPlaybook)}
                  >
                    {rosterLoading ? 'Suggesting…' : 'Suggest roster'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => void handleGenerateOntology()}
                    disabled={ontologyLoading || (!simulationObjective.trim() && !selectedPlaybook)}
                  >
                    {ontologyLoading ? 'Ontology…' : 'Generate ontology'}
                  </Button>
                  {lastGeneratedOntology ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setLastGeneratedOntology(null)}
                    >
                      Clear ontology
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
                    Ontology cached — the next &quot;Suggest roster&quot; will use it for extraction.
                  </p>
                ) : null}
                {parsedObjective?.summary != null && (
                  <p className="mt-2 text-xs text-foreground-muted line-clamp-3">
                    Parsed: {String(parsedObjective.summary)}
                  </p>
                )}
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
                    Enrich with live research (Tavily)
                  </span>
                  <span className="block text-xs text-foreground-muted mt-0.5">
                    Prefetch evidence packs; requires TAVILY_API_KEY on the server.
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
                        const err =
                          typeof p.error === 'string' ? p.error : undefined;
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

              <Slider
                label="Number of Rounds"
                min={5}
                max={50}
                value={rounds}
                onChange={setRounds}
              />

              <div>
                <label className="block text-sm font-medium text-foreground-muted mb-2">
                  Environment Type
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {SIMULATION_ENVIRONMENTS.map((env) => (
                    <button
                      key={env.value}
                      type="button"
                      onClick={() => setEnvironmentType(env.value)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        environmentType === env.value
                          ? 'border-accent bg-accent/10 text-accent'
                          : 'border-border bg-background-secondary/50 text-foreground-muted hover:border-border-hover'
                      }`}
                    >
                      <span className="block text-sm font-medium text-foreground">
                        {env.label}
                      </span>
                      <span className="block text-xs mt-1 text-foreground-muted leading-snug">
                        {env.description}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground-muted mb-2">
                  Model Selection (Optional)
                </label>
                {wizardLlmProvider ? (
                  <p className="text-xs text-foreground-muted mb-2">
                    Server LLM: <span className="text-foreground">{wizardLlmProvider}</span>
                    {wizardLlmModels.length === 0
                      ? ' — only the provider default applies (configure a cloud model in .env).'
                      : ' — pick a model id for this vendor or use Provider Default.'}
                  </p>
                ) : null}
                <div
                  className={`grid gap-3 ${
                    wizardLlmModels.length === 0
                      ? 'grid-cols-1 sm:grid-cols-1'
                      : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setModelSelection('')}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      modelSelection === ''
                        ? 'border-accent bg-accent/10'
                        : 'border-border bg-background-secondary/50 hover:border-border-hover'
                    }`}
                  >
                    <div className="font-medium text-foreground">Provider Default</div>
                    <div className="text-xs text-foreground-muted">
                      Use LLM_MODEL_NAME / provider default from the server
                    </div>
                  </button>
                  {wizardLlmModels.map((model) => (
                    <button
                      key={model.id}
                      type="button"
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
                        A saved model id from a previous session does not match this
                        server&apos;s LLM provider. Launch will use{' '}
                        <strong>Provider default</strong> until you pick a valid model or clear
                        this.
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
                  <h3 className="text-sm font-semibold text-foreground">
                    Simulation features
                  </h3>
                </div>
                <p className="text-xs text-foreground-muted">
                  Toggle optional work to balance quality, runtime, and API cost. Estimates
                  update automatically.
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
                      Generate a narrative report after the simulation completes (extra tokens
                      and ~1 min)
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
                    <span className="font-medium text-foreground text-sm">
                      Extended seed context
                    </span>
                    <span className="block text-xs text-foreground-muted mt-0.5">
                      Injects more characters from each seed document into agent prompts (backend
                      cap 100k chars per file vs 24k).
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
                          <span className="font-medium text-foreground text-sm">
                            Enable Monte Carlo
                          </span>
                          <span className="block text-xs text-foreground-muted mt-0.5">
                            After your main simulation finishes, the server runs additional sampled
                            runs (10–{INLINE_MONTE_CARLO_MAX_ITERATIONS}, server cap) and stores
                            summary stats under results. High token
                            cost.
                          </span>
                        </span>
                      </label>
                      {monteCarloEnabled && (
                        <Slider
                          label="Monte Carlo iterations"
                          min={10}
                          max={INLINE_MONTE_CARLO_MAX_ITERATIONS}
                          step={1}
                          value={Math.min(
                            INLINE_MONTE_CARLO_MAX_ITERATIONS,
                            Math.max(10, monteCarloIterations),
                          )}
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
        )}

        {currentStep === 4 && selectedPlaybook && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Review & Launch
              </h2>
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
                      <strong>Provider default</strong>. Go back to Set Parameters to choose a
                      model, or clear now.
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
                    <p className="text-foreground">
                      {simulationEnvironmentLabel(environmentType)}
                    </p>
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
                      <p className="text-foreground">
                        {selectedSeedIds.length} attached
                      </p>
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
        )}
      </Card>

      {/* Navigation */}
      <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={currentStep === 0}
          leftIcon={<ChevronLeft className="w-4 h-4" />}
          className="w-full sm:w-auto"
        >
          Back
        </Button>
        {currentStep < steps.length - 1 ? (
          <Button
            onClick={handleNext}
            disabled={!canProceed()}
            rightIcon={<ChevronRight className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            Next
          </Button>
        ) : (
          <Button
            onClick={handleLaunch}
            disabled={!canProceed() || isLoading}
            isLoading={isLoading}
            leftIcon={!isLoading ? <Check className="w-4 h-4" /> : undefined}
            className="w-full sm:w-auto"
          >
            Launch Simulation
          </Button>
        )}
      </div>
    </div>
  );
}
