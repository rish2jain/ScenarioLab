'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { Building2, ShieldAlert, Swords, Users, Loader2, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { Playbook } from '@/lib/types';

const iconMap: Record<string, ReactNode> = {
  Building2: <Building2 className="w-8 h-8" />,
  ShieldAlert: <ShieldAlert className="w-8 h-8" />,
  Swords: <Swords className="w-8 h-8" />,
  Users: <Users className="w-8 h-8" />,
};

/** Applies `?playbook=<id>` from the URL to the playbook store when playbooks load. */
export function PlaybookFromQuerySync({
  playbooks,
  setSelectedPlaybook,
}: {
  playbooks: Playbook[];
  setSelectedPlaybook: (p: Playbook) => void;
}) {
  const searchParams = useSearchParams();
  const appliedRef = useRef(false);
  useEffect(() => {
    if (appliedRef.current) return;
    const id = searchParams.get('playbook');
    if (!id || playbooks.length === 0) return;
    const match = playbooks.find((p) => p.id === id);
    if (match) {
      setSelectedPlaybook(match);
      appliedRef.current = true;
    }
  }, [searchParams, playbooks, setSelectedPlaybook]);
  return null;
}

export interface PlaybookSelectProps {
  playbooks: Playbook[];
  selectedPlaybook: Playbook | null;
  setSelectedPlaybook: (p: Playbook) => void;
  playbookDetailLoading: boolean;
  playbookDetailError: string | null;
  retryPlaybookDetail: () => void;
}

export function PlaybookSelect({
  playbooks,
  selectedPlaybook,
  setSelectedPlaybook,
  playbookDetailLoading,
  playbookDetailError,
  retryPlaybookDetail,
}: PlaybookSelectProps) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-foreground">Select a Playbook</h2>
      {playbooks.length === 0 ? (
        <div
          className="rounded-lg border border-border bg-background-secondary/50 p-8 text-center space-y-2"
          role="status"
        >
          <p className="font-medium text-foreground">No playbooks available</p>
          <p className="text-sm text-foreground-muted">
            Could not load playbook templates. Check that the backend is running, then refresh
            the page.
          </p>
        </div>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {playbooks.map((playbook) => (
          <button
            key={playbook.id}
            type="button"
            aria-pressed={selectedPlaybook?.id === playbook.id}
            onClick={() => setSelectedPlaybook(playbook)}
            className={`p-6 rounded-lg border-2 text-left transition-all ${
              selectedPlaybook?.id === playbook.id
                ? 'border-accent bg-accent/10'
                : 'border-border hover:border-border-hover bg-background-secondary/50'
            }`}
          >
            <div className="flex items-start gap-4">
              <div
                className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                  selectedPlaybook?.id === playbook.id
                    ? 'bg-accent/20 text-accent'
                    : 'bg-background-tertiary text-foreground-muted'
                }`}
              >
                {iconMap[playbook.icon] || <Building2 className="w-8 h-8" />}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-foreground">{playbook.name}</h3>
                  <Badge size="sm">{playbook.category}</Badge>
                </div>
                <p className="text-sm text-foreground-muted mt-1">{playbook.description}</p>
                <div className="flex items-center gap-4 mt-3 text-xs text-foreground-subtle">
                  <span>{playbook.typicalDuration}</span>
                  <span>•</span>
                  <span>{playbook.agentCount} agents</span>
                  <span>•</span>
                  <span>{playbook.rounds} rounds</span>
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
      )}
      {selectedPlaybook && playbookDetailLoading && (
        <div
          className="flex items-center gap-3 text-sm text-foreground-muted"
          role="status"
          aria-live="polite"
        >
          <Loader2 className="w-4 h-4 animate-spin text-accent flex-shrink-0" aria-hidden />
          <span>Loading playbook roster…</span>
        </div>
      )}
      {selectedPlaybook && playbookDetailError && !playbookDetailLoading && (
        <div
          className="flex flex-col gap-3 rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-sm text-foreground"
          role="alert"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" aria-hidden />
            <p>{playbookDetailError}</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            className="self-start"
            onClick={retryPlaybookDetail}
          >
            Retry loading playbook
          </Button>
        </div>
      )}
    </div>
  );
}
