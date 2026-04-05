/** LLM endpoints (wizard capabilities, etc.). */

import { fetchApi } from './client';

export interface InferenceCapabilities {
  hybridAvailable: boolean;
  localProvider: string | null;
  localModel: string | null;
  defaultInferenceMode: string;
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
        defaultInferenceMode: String(d.default_inference_mode ?? 'cloud'),
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
