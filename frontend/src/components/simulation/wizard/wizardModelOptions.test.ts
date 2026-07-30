import { describe, expect, it } from 'vitest';
import { mergeWizardModelOptions } from './wizardModelOptions';
import type { WizardModelOption } from '@/lib/types';

describe('mergeWizardModelOptions', () => {
  it('always includes exactly one provider-default option at the front', () => {
    const result = mergeWizardModelOptions([]);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: '',
      name: 'Provider Default',
      desc: 'Use the recommended model',
    });
  });

  it('dedupes server-provided empty-id provider default against the hardcoded one', () => {
    const server: WizardModelOption[] = [
      { id: '', name: 'Provider Default', desc: 'Use the provider default model' },
      { id: 'gpt-4o', name: 'GPT-4o', desc: 'Best balance' },
      { id: 'gpt-4', name: 'GPT-4', desc: 'High quality' },
    ];
    const result = mergeWizardModelOptions(server);
    expect(result.filter((m) => m.id === '' || m.name === 'Provider Default')).toHaveLength(1);
    expect(result[0].id).toBe('');
    expect(result.map((m) => m.id)).toEqual(['', 'gpt-4o', 'gpt-4']);
  });

  it('dedupes by id for non-empty model ids', () => {
    const server: WizardModelOption[] = [
      { id: 'gpt-4o', name: 'GPT-4o', desc: 'a' },
      { id: 'gpt-4o', name: 'GPT-4o duplicate', desc: 'b' },
    ];
    const result = mergeWizardModelOptions(server);
    expect(result.filter((m) => m.id === 'gpt-4o')).toHaveLength(1);
  });
});
