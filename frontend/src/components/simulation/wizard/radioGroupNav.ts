/** Compute the next index for a radiogroup roving-tabindex keyboard handler. */
export function nextRadioIndex(
  key: string,
  currentIndex: number,
  length: number
): number | null {
  if (length <= 0) return null;
  const idx = currentIndex < 0 ? 0 : currentIndex % length;
  switch (key) {
    case 'ArrowRight':
    case 'ArrowDown':
      return (idx + 1) % length;
    case 'ArrowLeft':
    case 'ArrowUp':
      return (idx - 1 + length) % length;
    case 'Home':
      return 0;
    case 'End':
      return length - 1;
    default:
      return null;
  }
}

export function rovingTabIndex(selected: boolean): 0 | -1 {
  return selected ? 0 : -1;
}
