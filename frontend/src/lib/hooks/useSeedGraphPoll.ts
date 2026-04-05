'use client';

import { useEffect } from 'react';
import { api } from '@/lib/api';
import type { UploadedFile } from '@/lib/types';
import { useUploadStore } from '@/lib/store';
import { useToast } from '@/components/ui/Toast';

function applySeedRowToStore(
  updateFile: (id: string, updates: Partial<UploadedFile>) => void,
  id: string,
  row: UploadedFile
): void {
  const patch: Partial<UploadedFile> = {
    status: row.status,
    progress:
      row.status === 'completed' ? 100 : row.status === 'error' ? 0 : 90,
  };
  if (row.status === 'error' && row.errorMessage) {
    patch.errorMessage = row.errorMessage;
  } else if (row.status === 'completed' || row.status === 'processing') {
    patch.errorMessage = undefined;
  }
  updateFile(id, patch);
}

/**
 * While any upload-store file is in `processing`, periodically refresh status from GET /api/seeds
 * so the UI reflects deferred graph extraction without blocking uploadFile/processSeeds.
 *
 * Uses GET /api/seeds/{id} when the list response omits a seed or list fails, so rows do not
 * stay stuck in `processing` after the graph step completes.
 */
export function useSeedGraphPoll(): void {
  const files = useUploadStore((s) => s.files);
  const updateFile = useUploadStore((s) => s.updateFile);
  const { addToast } = useToast();

  const processingKey = files
    .filter((f) => f.status === 'processing')
    .map((f) => f.id)
    .sort()
    .join(',');

  useEffect(() => {
    if (!processingKey) return;

    const ids = processingKey.split(',').filter(Boolean);
    let consecutiveFailures = 0;
    let warned = false;

    const tick = async () => {
      try {
        const seeds = await api.listSeeds();
        consecutiveFailures = 0;
        warned = false;
        for (const id of ids) {
          let row = seeds.find((s) => s.id === id);
          if (!row) {
            row = (await api.getSeed(id)) ?? undefined;
          }
          if (!row) continue;
          applySeedRowToStore(updateFile, id, row);
        }
      } catch {
        consecutiveFailures += 1;
        if (!warned && consecutiveFailures >= 3) {
          warned = true;
          addToast(
            'Could not refresh document processing status. Uploaded files may stay in processing until the backend becomes reachable.',
            'error'
          );
        }
        for (const id of ids) {
          try {
            const row = await api.getSeed(id);
            if (row) applySeedRowToStore(updateFile, id, row);
          } catch {
            /* offline */
          }
        }
      }
    };

    void tick();
    const t = setInterval(tick, 2500);

    const onVis = () => {
      if (document.visibilityState === 'visible') void tick();
    };
    document.addEventListener('visibilitychange', onVis);

    return () => {
      clearInterval(t);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [processingKey, updateFile, addToast]);
}
