'use client';

import { useState, useEffect, useRef } from 'react';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { Playbook } from '@/lib/types';
import { shouldApplyPlaybookConfigDefaults } from './playbookConfigGate';

/** Lazy-load playbook roster after selection; configure default agent counts. */
export function usePlaybookDetail({
  selectedPlaybook,
  setSelectedPlaybook,
  setSimulationName,
  setAgentConfigs,
}: {
  selectedPlaybook: Playbook | null;
  setSelectedPlaybook: (p: Playbook) => void;
  setSimulationName: (updater: string | ((prev: string) => string)) => void;
  setAgentConfigs: (
    updater:
      | Record<string, number>
      | ((prev: Record<string, number>) => Record<string, number>),
  ) => void;
}) {
  const { addToast } = useToast();
  /** True while lazy-loading full playbook (roster) after selection — blocks Next on step 0. */
  const [playbookDetailLoading, setPlaybookDetailLoading] = useState(false);
  /** Set when detail fetch fails so the user sees why Next stays disabled; cleared on retry/success. */
  const [playbookDetailError, setPlaybookDetailError] = useState<string | null>(null);
  /** Increment to re-run the detail fetch for the same selection (Retry). */
  const [playbookDetailRetryToken, setPlaybookDetailRetryToken] = useState(0);

  const fetchedIdRef = useRef<string | null>(null);
  /** Last playbook id for which roster defaults + default name were applied. */
  const configuredPlaybookIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!selectedPlaybook) {
      fetchedIdRef.current = null;
      configuredPlaybookIdRef.current = null;
      setPlaybookDetailLoading(false);
      setPlaybookDetailError(null);
      return;
    }

    let cancelled = false;
    const targetId = selectedPlaybook.id;

    const loadAndConfigure = async () => {
      const needsRosterFetch =
        (!selectedPlaybook.roster || selectedPlaybook.roster.length === 0) &&
        fetchedIdRef.current !== targetId;
      if (needsRosterFetch) {
        fetchedIdRef.current = targetId;
        setPlaybookDetailLoading(true);
      }
      setPlaybookDetailError(null);
      try {
        let playbook = selectedPlaybook;
        if (needsRosterFetch) {
          const full = await api.getPlaybook(targetId);
          if (cancelled) return;
          if (full === null) {
            fetchedIdRef.current = null;
            const msg =
              'Playbook details could not be loaded. It may have been removed or unavailable.';
            setPlaybookDetailError(msg);
            addToast(msg, 'error');
            return;
          }
          setSelectedPlaybook(full);
          playbook = full;
        }

        if (cancelled) return;

        // Apply roster defaults / default name only when the playbook *id* changes,
        // not when the same selection is replaced with a new object (e.g. after fetch).
        if (
          !shouldApplyPlaybookConfigDefaults(
            configuredPlaybookIdRef.current,
            playbook.id
          )
        ) {
          return;
        }
        configuredPlaybookIdRef.current = playbook.id;

        const roster = playbook.roster ?? [];
        const configs: Record<string, number> = {};
        roster.forEach((role) => {
          configs[role.role] = role.defaultCount;
        });
        setAgentConfigs(configs);
        setSimulationName((prev) =>
          prev ? prev : `${playbook.name} - ${new Date().toLocaleDateString()}`
        );
      } catch (err) {
        if (cancelled) return;
        console.error('getPlaybook failed', err);
        const msg =
          err instanceof Error
            ? err.message
            : 'Could not load playbook details.';
        setPlaybookDetailError(msg);
        addToast(msg, 'error');
      } finally {
        if (!cancelled) {
          setPlaybookDetailLoading(false);
        }
      }
    };

    void loadAndConfigure();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable setters/addToast omitted; deps are playbook + retry only
  }, [selectedPlaybook, playbookDetailRetryToken]);

  const retryPlaybookDetail = () => setPlaybookDetailRetryToken((t) => t + 1);

  return {
    playbookDetailLoading,
    playbookDetailError,
    retryPlaybookDetail,
  };
}
