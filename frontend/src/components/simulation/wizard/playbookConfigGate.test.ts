import { describe, expect, it } from 'vitest';
import { shouldApplyPlaybookConfigDefaults } from './playbookConfigGate';

describe('shouldApplyPlaybookConfigDefaults', () => {
  it('applies when no playbook has been configured yet', () => {
    expect(shouldApplyPlaybookConfigDefaults(null, 'pb-1')).toBe(true);
  });

  it('skips when the same playbook id is already configured', () => {
    expect(shouldApplyPlaybookConfigDefaults('pb-1', 'pb-1')).toBe(false);
  });

  it('applies when selecting a different playbook', () => {
    expect(shouldApplyPlaybookConfigDefaults('pb-1', 'pb-2')).toBe(true);
  });
});
