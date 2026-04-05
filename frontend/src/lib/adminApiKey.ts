/**
 * Browser session storage for the backend ADMIN_API_KEY (Bearer) used only to
 * call /api/v1/api-keys management endpoints. Never embed this in NEXT_PUBLIC_*.
 */
const STORAGE_KEY = 'scenariolab_admin_api_key';

export function getAdminApiKey(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = sessionStorage.getItem(STORAGE_KEY)?.trim();
    return v && v.length > 0 ? v : null;
  } catch {
    return null;
  }
}

export function setAdminApiKey(key: string): void {
  sessionStorage.setItem(STORAGE_KEY, key.trim());
}

export function clearAdminApiKey(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function adminAuthHeaders(): Record<string, string> {
  const k = getAdminApiKey();
  if (!k) return {};
  return { Authorization: `Bearer ${k}` };
}
