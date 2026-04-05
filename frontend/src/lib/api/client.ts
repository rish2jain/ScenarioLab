// API client — shared fetch helper and base URL config
import type { ApiResponse } from '../types';

const envApiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
export const API_BASE_URL = envApiBaseUrl ?? '';

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

/**
 * Read body once (avoids empty-body `response.json()` throws), then parse JSON.
 * Tries `JSON.parse` inside try/catch; returns null for empty or non-JSON bodies.
 */
async function parseSuccessJsonBody(response: Response): Promise<unknown | null> {
  let text: string;
  try {
    text = await response.text();
  } catch {
    return null;
  }
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return null;
  }
}

/** Typed fetch wrapper. Returns ApiResponse<T> with success=false on network or HTTP errors. */
export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const defaultHeaders: Record<string, string> = {};
    // Only set Content-Type for non-FormData requests
    if (!(options?.body instanceof FormData)) {
      defaultHeaders['Content-Type'] = 'application/json';
    }
    const url = `${API_BASE_URL}${endpoint}`;
    const { headers: optionHeadersInit, ...restOptions } = options ?? {};
    const mergedHeaders = new Headers(defaultHeaders);
    if (optionHeadersInit !== undefined) {
      new Headers(optionHeadersInit).forEach((value, key) => {
        mergedHeaders.set(key, value);
      });
    }
    const response = await fetch(url, {
      ...restOptions,
      headers: mergedHeaders,
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
        // non-JSON error body
      }
      console.warn(`API call failed for ${endpoint}:`, errorMessage);
      return { success: false, error: errorMessage, status: response.status };
    }

    const parsed = await parseSuccessJsonBody(response);
    if (parsed === null) {
      return { success: true, data: undefined };
    }
    return { success: true, data: parsed as T };
  } catch (error) {
    console.warn(`API call failed for ${endpoint}:`, error);
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: message };
  }
}
