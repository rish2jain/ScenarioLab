'use client';

import { useState, useEffect, useMemo } from 'react';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { Playbook, UploadedFile } from '@/lib/types';
import type { ObjectiveMode } from './types';

/** Parse objective, suggest roster, ontology, and research preflight tooling. */
export function useObjectiveTools({
  simulationObjective,
  objectiveMode,
  selectedPlaybook,
  setAgentConfigs,
  uploadedFiles,
  selectedSeedIds,
  simulationName,
}: {
  simulationObjective: string;
  objectiveMode: ObjectiveMode;
  selectedPlaybook: Playbook | null;
  setAgentConfigs: (
    updater:
      | Record<string, number>
      | ((prev: Record<string, number>) => Record<string, number>),
  ) => void;
  uploadedFiles: UploadedFile[];
  selectedSeedIds: string[];
  simulationName: string;
}) {
  const { addToast } = useToast();
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

  /** Sorted id:name labels; memoized so identity is stable when only unrelated uploads change. */
  const seedLabels = useMemo(
    () =>
      selectedSeedIds.map((id) => `${id}:${fileIdToName[id] ?? ''}`).sort(),
    [selectedSeedIds, fileIdToName],
  );

  /** Same inputs as `handlePrefetchResearch` seed texts; if these drift, cached packs are invalid. */
  const researchPrefetchFingerprint = useMemo(() => {
    const objective = simulationObjective.trim();
    return JSON.stringify({
      objective,
      seedLabels,
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

  return {
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
  };
}
