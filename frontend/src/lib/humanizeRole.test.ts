import { describe, expect, it } from 'vitest';
import { humanizeRole } from './humanizeRole';

describe('humanizeRole', () => {
  it('converts snake_case to Title Case', () => {
    expect(humanizeRole('board_member')).toBe('Board Member');
    expect(humanizeRole('activist_investor')).toBe('Activist Investor');
  });

  it('handles already human labels', () => {
    expect(humanizeRole('CEO')).toBe('Ceo');
  });

  it('returns empty for blank', () => {
    expect(humanizeRole('  ')).toBe('');
  });
});
