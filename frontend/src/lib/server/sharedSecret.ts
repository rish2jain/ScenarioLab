/** Server-only: backend API_SHARED_SECRET (never NEXT_PUBLIC_*). */

export function getServerApiSharedSecret(): string {
  return process.env.API_SHARED_SECRET?.trim() ?? '';
}

/** Inject X-ScenarioLab-Secret when the server env secret is set. */
export function applySharedSecretHeader(headers: Headers): void {
  const secret = getServerApiSharedSecret();
  if (secret) {
    headers.set('X-ScenarioLab-Secret', secret);
  }
}
