/** Seed IDs that are selected and usable for simulation / extended context. */
export function filterValidSeedIds(
  selectedSeedIds: string[],
  uploadedFiles: Array<{ id: string; status: string }>
): string[] {
  return selectedSeedIds.filter((id) =>
    uploadedFiles.some(
      (f) =>
        f.id === id &&
        (f.status === 'completed' || f.status === 'processing')
    )
  );
}

/** Gate extended seed context on successfully uploaded selections only. */
export function resolveExtendedSeedContext(
  extendedSeedContext: boolean,
  validSeedIds: string[]
): boolean {
  return extendedSeedContext && validSeedIds.length > 0;
}
