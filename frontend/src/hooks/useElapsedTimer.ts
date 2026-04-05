'use client';

import { useEffect, useRef, useState } from 'react';
import type { Simulation } from '@/lib/types';

export function useElapsedTimer(
  currentSimulation: Simulation | null | undefined,
  elapsedStorageKey: string
): number {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const startedAtRef = useRef<number | null>(null);

  // Elapsed time ticker while running — persist to sessionStorage so navigating
  // to feature tabs (unmount) does not reset the clock when the API omits elapsedTime.
  useEffect(() => {
    // Cleared on cleanup so a tick cannot call setElapsedSeconds after unmount.
    let cancelled = false;
    const isActive =
      currentSimulation?.status === 'running' ||
      currentSimulation?.status === 'generating_report';

    if (!isActive) {
      if (startedAtRef.current !== null) {
        const sec = Math.floor((Date.now() - startedAtRef.current) / 1000);
        try {
          sessionStorage.setItem(elapsedStorageKey, String(sec));
        } catch {
          /* ignore quota / private mode */
        }
        startedAtRef.current = null;
      }
      const st = currentSimulation?.status;
      if (
        st === 'completed' ||
        st === 'pending' ||
        st === 'cancelled' ||
        st === 'failed'
      ) {
        try {
          sessionStorage.removeItem(elapsedStorageKey);
        } catch {
          /* ignore */
        }
      }
      return;
    }

    if (startedAtRef.current === null) {
      const fromApi = currentSimulation?.elapsedTime;
      let stored = NaN;
      try {
        const raw = sessionStorage.getItem(elapsedStorageKey);
        if (raw != null) stored = parseInt(raw, 10);
      } catch {
        /* ignore */
      }
      const previousElapsed =
        typeof fromApi === 'number' && fromApi >= 0 && !Number.isNaN(fromApi)
          ? fromApi
          : !Number.isNaN(stored) && stored >= 0
            ? stored
            : 0;
      startedAtRef.current = Date.now() - previousElapsed * 1000;
      queueMicrotask(() => {
        if (!cancelled) setElapsedSeconds(previousElapsed);
      });
    }

    const timer = setInterval(() => {
      if (cancelled) return;
      if (startedAtRef.current === null) return;
      const sec = Math.floor((Date.now() - startedAtRef.current) / 1000);
      setElapsedSeconds(sec);
      try {
        sessionStorage.setItem(elapsedStorageKey, String(sec));
      } catch {
        /* ignore */
      }
    }, 1000);

    return () => {
      cancelled = true;
      clearInterval(timer);
      if (startedAtRef.current !== null) {
        const sec = Math.floor((Date.now() - startedAtRef.current) / 1000);
        try {
          sessionStorage.setItem(elapsedStorageKey, String(sec));
        } catch {
          /* ignore */
        }
        startedAtRef.current = null;
      }
    };
    // Intentionally omit currentSimulation?.elapsedTime: polling updates would reset startedAtRef via cleanup.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hydrate once when status becomes running; see above
  }, [currentSimulation?.status, elapsedStorageKey]);

  // After remount while paused, restore elapsed for display when the API has no field.
  const pausedStatus = currentSimulation?.status;
  const pausedElapsedFromApi = currentSimulation?.elapsedTime;
  useEffect(() => {
    if (pausedStatus !== 'paused') return;
    const fromApi = pausedElapsedFromApi;
    if (typeof fromApi === 'number' && fromApi >= 0) return;
    try {
      const raw = sessionStorage.getItem(elapsedStorageKey);
      if (raw == null) return;
      const n = parseInt(raw, 10);
      if (Number.isNaN(n) || n < 0) return;
      queueMicrotask(() => setElapsedSeconds(n));
    } catch {
      /* ignore */
    }
  }, [pausedStatus, pausedElapsedFromApi, elapsedStorageKey]);

  return elapsedSeconds;
}
