/** LLM endpoints (wizard capabilities, etc.). */

import { fetchApi } from './client';

/** Matches backend `inference_mode` / `default_inference_mode` vocabulary (`config.py`). */
export type DefaultInferenceMode = 'cloud' | 'hybrid' | 'local';

function normalizeDefaultInferenceMode(raw: unknown): DefaultInferenceMode {
  const s = String(raw ?? 'cloud')
    .trim()
    .toLowerCase();
  if (s === 'hybrid' || s === 'local' || s === 'cloud') return s;
  return 'cloud';
}

export interface InferenceCapabilities {
  hybridAvailable: boolean;
  localProvider: string | null;
  localModel: string | null;
  defaultInferenceMode: DefaultInferenceMode;
}

export const llmApi = {
  async getInferenceCapabilities(): Promise<InferenceCapabilities> {
    const result = await fetchApi<Record<string, unknown>>('/api/llm/capabilities');
    if (result.success && result.data) {
      const d = result.data;
      return {
        hybridAvailable: Boolean(d.hybrid_available),
        localProvider:
          d.local_provider != null ? String(d.local_provider) : null,
        localModel: d.local_model != null ? String(d.local_model) : null,
        defaultInferenceMode: normalizeDefaultInferenceMode(
          d.default_inference_mode
        ),
      };
    }
    return {
      hybridAvailable: false,
      localProvider: null,
      localModel: null,
      defaultInferenceMode: 'cloud',
    };
  },
};
