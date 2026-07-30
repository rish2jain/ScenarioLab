'use client';

import { useState, useEffect, useMemo } from 'react';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { WizardModelOption } from '@/lib/types';

/** Fetch wizard model list and reconcile draft modelSelection against the server vendor. */
export function useWizardModels(
  modelSelection: string,
  setModelSelection: (id: string) => void,
) {
  const { addToast } = useToast();
  const [wizardLlmModels, setWizardLlmModels] = useState<WizardModelOption[]>([]);
  const [wizardLlmProvider, setWizardLlmProvider] = useState<string>('');

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
  }, [wizardLlmModels, modelSelection, wizardLlmProvider, setModelSelection]);

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

  return {
    wizardLlmModels,
    wizardLlmProvider,
    effectiveModelSelection,
    staleSavedModelId,
    modelSelectionLabel,
  };
}
