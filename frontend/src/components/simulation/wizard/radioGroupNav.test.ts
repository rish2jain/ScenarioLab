import { describe, expect, it } from 'vitest';
import { nextRadioIndex, rovingTabIndex } from './radioGroupNav';

describe('nextRadioIndex', () => {
  it('moves with arrows and wraps', () => {
    expect(nextRadioIndex('ArrowRight', 0, 3)).toBe(1);
    expect(nextRadioIndex('ArrowDown', 2, 3)).toBe(0);
    expect(nextRadioIndex('ArrowLeft', 0, 3)).toBe(2);
    expect(nextRadioIndex('ArrowUp', 1, 3)).toBe(0);
  });

  it('supports Home and End', () => {
    expect(nextRadioIndex('Home', 2, 4)).toBe(0);
    expect(nextRadioIndex('End', 0, 4)).toBe(3);
  });

  it('returns null for unrelated keys or empty groups', () => {
    expect(nextRadioIndex('Enter', 0, 3)).toBeNull();
    expect(nextRadioIndex('ArrowRight', 0, 0)).toBeNull();
  });
});

describe('rovingTabIndex', () => {
  it('only the selected option is tabbable', () => {
    expect(rovingTabIndex(true)).toBe(0);
    expect(rovingTabIndex(false)).toBe(-1);
  });
});
