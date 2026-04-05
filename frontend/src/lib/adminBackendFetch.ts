import type { ApiResponse } from './types';

/** Parse FastAPI `detail` (string, object, or validation error list) for user-facing messages. */
function formatFastApiDetail(raw: unknown): string | null {
  if (raw == null) return null;
  if (typeof raw === 'string') return raw;
  if (Array.isArray(raw)) {
    const parts = raw.map((item) => {
      if (typeof item === 'object' && item !== null && 'msg' in item) {
        return String((item as { msg?: string }).msg ?? '');
      }
      return typeof item === 'string' ? item : JSON.stringify(item);
    });
    const joined = parts.filter(Boolean).join('; ');
    return joined || null;
  }
  if (typeof raw === 'object' && raw !== null && 'msg' in raw) {
    return String((raw as { msg: string }).msg);
  }
  return null;
}

function hasContentTypeKey(headers: Record<string, string>): boolean {
  return Object.keys(headers).some((k) => k.toLowerCase() === 'content-type');
}

/** Build a plain header map without spreading a `Headers` instance (spread yields {}). */
function headersInitToRecord(init: HeadersInit | undefined): Record<string, string> {
  if (init == null) return {};
  if (init instanceof Headers) {
    const out: Record<string, string> = {};
    init.forEach((value, key) => {
      out[key] = value;
    });
    return out;
  }
  if (Array.isArray(init)) {
    const out: Record<string, string> = {};
    for (const pair of init) {
      if (pair.length >= 2) {
        out[String(pair[0])] = String(pair[1]);
      }
    }
    return out;
  }
  return { ...init };
}

function contentTypeIsJson(value: string | null): boolean {
  if (value == null || value === '') return false;
  const lower = value.toLowerCase();
  return lower.includes('application/json') || lower.includes('+json');
}

/**
 * Same-origin admin BFF: forwards to `/api/admin/backend/...` with credentials.
 * The backend admin secret stays on the server; the browser only holds an httpOnly session cookie.
 */
export async function fetchAdminBackend<T>(
  path: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const url = `/api/admin/backend${normalized}`;

  try {
    const headers: Record<string, string> = headersInitToRecord(options?.headers);
    if (
      options?.body != null &&
      !(options.body instanceof FormData) &&
      !hasContentTypeKey(headers)
    ) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      credentials: 'include',
      headers,
    });

    if (!response.ok) {
      let errorMessage = `Request failed (${response.status})`;
      try {
        const errBody = (await response.json()) as {
          detail?: unknown;
          message?: string;
        };
        const detail = formatFastApiDetail(errBody?.detail);
        if (detail) {
          errorMessage = detail;
        } else if (typeof errBody?.message === 'string') {
          errorMessage = errBody.message;
        }
      } catch {
        /* non-JSON */
      }
      console.warn(`Admin BFF call failed for ${normalized}:`, errorMessage);
      return { success: false, error: errorMessage, status: response.status };
    }

    const contentType = response.headers.get('content-type');
    const raw = await response.text();
    const trimmed = raw.trim();
    if (!trimmed || !contentTypeIsJson(contentType)) {
      return { success: true, data: undefined };
    }
    try {
      const data = JSON.parse(trimmed) as T;
      return { success: true, data };
    } catch {
      return { success: true, data: undefined };
    }
  } catch (error) {
    console.warn(`Admin BFF call failed for ${normalized}:`, error);
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: message };
  }
}
