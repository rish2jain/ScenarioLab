import type { WizardModelOption } from '@/lib/types';

/** Hardcoded provider-default option shown when the server list is empty or lacks one. */
export const PROVIDER_DEFAULT_OPTION: WizardModelOption = {
  id: '',
  name: 'Provider Default',
  desc: 'Use the recommended model',
};

/**
 * Merge server wizard models with a single provider-default card.
 * Backend lists often prepend an empty-id "Provider Default"; the UI used to
 * also hardcode one — this keeps exactly one empty-id option at the front.
 */
export function mergeWizardModelOptions(
  serverModels: WizardModelOption[]
): WizardModelOption[] {
  const seen = new Set<string>();
  const merged: WizardModelOption[] = [];

  const pushUnique = (model: WizardModelOption) => {
    const key = model.id === '' ? '__provider_default__' : model.id;
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(model);
  };

  pushUnique(PROVIDER_DEFAULT_OPTION);
  for (const model of serverModels) {
    if (model.id === '') {
      // Keep our canonical provider-default copy; skip server duplicate.
      continue;
    }
    pushUnique(model);
  }

  return merged;
}
