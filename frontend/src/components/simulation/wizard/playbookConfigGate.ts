/** True when roster defaults should be applied for this playbook selection. */
export function shouldApplyPlaybookConfigDefaults(
  configuredPlaybookId: string | null,
  playbookId: string
): boolean {
  return configuredPlaybookId !== playbookId;
}
