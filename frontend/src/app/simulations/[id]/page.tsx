'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Play,
  Pause,
  Square,
  MessageSquare,
  FileText,
  ChevronLeft,
  Clock,
  Users,
  Mic,
  Target,
  Users2,
  History,
  PieChart,
  BarChart3,
  Network,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { RoundIndicator } from '@/components/simulation/RoundIndicator';
import { SimulationFeed } from '@/components/simulation/SimulationFeed';
import { AgentCard } from '@/components/simulation/AgentCard';
import { useSimulationStore } from '@/lib/store';
import { useElapsedTimer } from '@/hooks/useElapsedTimer';
import { api } from '@/lib/api';
import { fetchApi } from '@/lib/api/client';
import {
  createAgentColorAllocator,
  normalizeSimulation,
  normalizeAgentMessage,
} from '@/lib/api/normalizers';
import type { AgentMessage } from '@/lib/types';

const POLL_BASE_MS = 2000;
const POLL_MAX_DELAY_MS = 60_000;
const POLL_BACKOFF_FACTOR = 2;
const POLL_FAILURES_TOAST = 3;
const POLL_MAX_FAILURES = 10;

function FeatureCard({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link href={href}>
      <div className="flex flex-col items-center gap-1 p-2 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-colors cursor-pointer">
        <div className="text-slate-400">{icon}</div>
        <span className="text-xs text-slate-300">{label}</span>
      </div>
    </Link>
  );
}

export default function SimulationMonitorPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  const { addToast } = useToast();

  const {
    currentSimulation,
    setCurrentSimulation,
    agentMessages,
    setAgentMessages,
  } = useSimulationStore();

  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [controlLoading, setControlLoading] = useState<
    'start' | 'pause' | 'resume' | 'stop' | null
  >(null);
  const pollFailuresRef = useRef(0);
  const pollDelayMsRef = useRef(POLL_BASE_MS);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const elapsedStorageKey = `scenariolab-sim-elapsed-${simulationId}`;
  const elapsedSeconds = useElapsedTimer(currentSimulation, elapsedStorageKey);

  const messageAgentColors = useMemo(
    () => createAgentColorAllocator(),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `simulationId` is only in the deps so `createAgentColorAllocator` runs again when the route changes; the factory does not read `simulationId`.
    [simulationId],
  );

  // Fetch simulation state + messages (reusable for initial load and polling)
  const refreshSimulation = useCallback(async () => {
    let simulationData: Awaited<ReturnType<typeof api.getSimulation>>;
    let messagesData: AgentMessage[];
    try {
      [simulationData, messagesData] = await Promise.all([
        api.getSimulation(simulationId),
        api.getAgentMessages(simulationId, messageAgentColors),
      ]);
    } catch (error) {
      setCurrentSimulation(null);
      setNotFound(false);
      setAgentMessages([]);
      setLoadError(
        error instanceof Error
          ? error.message
          : 'Could not load this simulation. Check your connection and try again.'
      );
      return undefined;
    }
    if (simulationData === undefined) {
      setCurrentSimulation(null);
      setNotFound(false);
      setLoadError(
        'Could not load this simulation (API unreachable or server error). Check your connection and that the backend is running, then retry.'
      );
    } else if (simulationData === null) {
      setCurrentSimulation(null);
      setNotFound(true);
      setLoadError(null);
    } else {
      setCurrentSimulation(simulationData);
      setNotFound(false);
      setLoadError(null);
    }
    setAgentMessages(messagesData);
    return simulationData;
  }, [simulationId, messageAgentColors, setCurrentSimulation, setAgentMessages]);

  /** Poll refresh using raw fetch results so transient API failures can be detected (fetchApi does not throw). */
  const pollSimulation = useCallback(async (): Promise<boolean> => {
    const [simRes, msgRes] = await Promise.all([
      fetchApi<unknown>(`/api/simulations/${simulationId}`),
      fetchApi<Record<string, unknown>[]>(`/api/simulations/${simulationId}/messages`),
    ]);

    let messagesData: AgentMessage[];
    if (msgRes.success && msgRes.data) {
      messagesData = msgRes.data.map((m) =>
        normalizeAgentMessage(m, messageAgentColors)
      );
    } else if (msgRes.status === 404) {
      messagesData = [];
    } else {
      return false;
    }

    if (simRes.success && simRes.data) {
      setCurrentSimulation(
        normalizeSimulation(simRes.data as Record<string, unknown>)
      );
      setNotFound(false);
      setAgentMessages(messagesData);
      return true;
    }
    if (simRes.status === 404) {
      setCurrentSimulation(null);
      setNotFound(true);
      setAgentMessages(messagesData);
      return true;
    }
    return false;
  }, [simulationId, messageAgentColors, setCurrentSimulation, setAgentMessages]);

  // Initial load
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      await refreshSimulation();
      setIsLoading(false);
    };
    load();
  }, [refreshSimulation]);

  // Poll while running/paused with backoff + error handling (fetchApi does not throw)
  useEffect(() => {
    if (notFound) return;
    const status = currentSimulation?.status;
    if (status !== 'running' && status !== 'paused' && status !== 'generating_report') return;

    pollFailuresRef.current = 0;
    pollDelayMsRef.current = POLL_BASE_MS;
    setPollError(null);

    let cancelled = false;

    const scheduleNext = () => {
      pollTimeoutRef.current = setTimeout(async () => {
        if (cancelled) return;
        let ok = false;
        try {
          ok = await pollSimulation();
        } catch {
          ok = false;
        }
        if (cancelled) return;

        if (ok) {
          pollFailuresRef.current = 0;
          pollDelayMsRef.current = POLL_BASE_MS;
          setPollError(null);
        } else {
          pollFailuresRef.current += 1;
          const f = pollFailuresRef.current;
          pollDelayMsRef.current = Math.min(
            POLL_MAX_DELAY_MS,
            Math.round(pollDelayMsRef.current * POLL_BACKOFF_FACTOR)
          );
          if (f === POLL_FAILURES_TOAST) {
            addToast(
              'Could not refresh simulation data. Retrying with longer delays…',
              'error'
            );
            setPollError(
              'Live updates are struggling. Retrying with backoff. Check your connection.'
            );
          }
          if (f >= POLL_MAX_FAILURES) {
            addToast(
              'Stopped live updates after repeated refresh failures.',
              'error'
            );
            setPollError(
              'Live updates stopped after repeated failures. Refresh the page or check your connection.'
            );
            return;
          }
        }
        scheduleNext();
      }, pollDelayMsRef.current);
    };

    scheduleNext();

    return () => {
      cancelled = true;
      if (pollTimeoutRef.current !== null) {
        clearTimeout(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
    };
  }, [
    addToast,
    currentSimulation?.status,
    notFound,
    pollSimulation,
  ]);

  const handleControl = async (action: 'start' | 'pause' | 'resume' | 'stop') => {
    setControlLoading(action);
    try {
      await api.controlSimulation(simulationId, action);
      // Refresh immediately after control action to get real state
      await refreshSimulation();
    } catch (error) {
      console.error('Control action failed:', error);
      addToast(
        error instanceof Error
          ? error.message
          : `Could not ${action} simulation.`,
        'error'
      );
    } finally {
      setControlLoading(null);
    }
  };

  const formatElapsedTime = (seconds?: number) => {
    if (!seconds) return '00:00:00';
    const hrs = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const mins = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${hrs}:${mins}:${secs}`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading simulation...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <Card className="mt-8 mx-auto max-w-2xl">
        <EmptyState
          title="Could not load simulation"
          description={loadError}
          icon={<Square className="w-8 h-8" />}
          action={{
            label: 'Retry',
            onClick: () => {
              setLoadError(null);
              setIsLoading(true);
              void (async () => {
                await refreshSimulation();
                setIsLoading(false);
              })();
            },
          }}
        />
      </Card>
    );
  }

  if (!currentSimulation || notFound) {
    return (
      <Card className="mt-8 mx-auto max-w-2xl">
        <EmptyState
          title="Simulation not found"
          description="We couldn't find the simulation you're looking for. It may have been deleted or never existed."
          icon={<Square className="w-8 h-8" />}
          action={{
            label: 'Back to Simulations',
            onClick: () => router.push('/simulations')
          }}
        />
      </Card>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <Link href="/simulations">
              <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
                Back
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-lg md:text-xl font-bold text-slate-100 truncate">
                {currentSimulation.name}
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                {currentSimulation.playbookName}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Inference:{' '}
                {currentSimulation.config.inferenceMode === 'hybrid'
                  ? 'Hybrid (cloud-primed)'
                  : currentSimulation.config.inferenceMode === 'local'
                    ? 'Local'
                    : 'Cloud'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-slate-400">
              <Clock className="w-4 h-4" />
              <span className="font-mono">
                {formatElapsedTime(
                  currentSimulation.status === 'running' || currentSimulation.status === 'generating_report'
                    ? elapsedSeconds
                    : (currentSimulation.elapsedTime ?? elapsedSeconds)
                )}
              </span>
            </div>
            <StatusBadge status={currentSimulation.status} />
            <div className="flex items-center gap-2">
              <Link href={`/simulations/${simulationId}/chat`}>
                <Button variant="secondary" size="sm" leftIcon={<MessageSquare className="w-4 h-4" />}>
                  Chat
                </Button>
              </Link>
              {currentSimulation.status === 'completed' && (
                <Link href={`/simulations/${simulationId}/report`}>
                  <Button variant="secondary" size="sm" leftIcon={<FileText className="w-4 h-4" />}>
                    Report
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>

        {pollError && (
          <div
            className="mt-3 px-3 py-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm"
            role="alert"
          >
            {pollError}
          </div>
        )}

        {/* Feature Navigation Cards */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          <FeatureCard
            href={`/simulations/${simulationId}/network`}
            icon={<Network className="w-4 h-4" />}
            label="Network"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/timeline`}
            icon={<Clock className="w-4 h-4" />}
            label="Timeline"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/sensitivity`}
            icon={<BarChart3 className="w-4 h-4" />}
            label="Sensitivity"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/voice`}
            icon={<Mic className="w-4 h-4" />}
            label="Voice"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/zopa`}
            icon={<Target className="w-4 h-4" />}
            label="ZOPA"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/rehearsal`}
            icon={<Users2 className="w-4 h-4" />}
            label="Rehearsal"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/audit-trail`}
            icon={<History className="w-4 h-4" />}
            label="Audit"
          />
          <FeatureCard
            href={`/simulations/${simulationId}/attribution`}
            icon={<PieChart className="w-4 h-4" />}
            label="Attribution"
          />
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <RoundIndicator
            currentRound={currentSimulation.currentRound}
            totalRounds={currentSimulation.totalRounds}
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Feed */}
        <div className="flex-1 flex flex-col min-w-0 order-2 lg:order-1">
          <SimulationFeed messages={agentMessages} />
          
          {/* Controls */}
          <div className="px-4 md:px-6 py-3 md:py-4 border-t border-slate-700 bg-slate-800/50">
            <div className="flex flex-wrap items-center gap-2">
                {currentSimulation.status === 'running' ? (
                  <Button
                    variant="secondary"
                    leftIcon={<Pause className="w-4 h-4" />}
                    isLoading={controlLoading === 'pause'}
                    disabled={controlLoading !== null}
                    onClick={() => handleControl('pause')}
                  >
                    Pause
                  </Button>
                ) : currentSimulation.status === 'paused' ? (
                  <Button
                    leftIcon={<Play className="w-4 h-4" />}
                    isLoading={controlLoading === 'resume'}
                    disabled={controlLoading !== null}
                    onClick={() => handleControl('resume')}
                  >
                    Resume
                  </Button>
                ) : currentSimulation.status === 'pending' ? (
                  <Button
                    leftIcon={<Play className="w-4 h-4" />}
                    isLoading={controlLoading === 'start'}
                    disabled={controlLoading !== null}
                    onClick={() => handleControl('start')}
                  >
                    Start
                  </Button>
                ) : null}
                
                {currentSimulation.status === 'generating_report' && (
                  <span className="text-sm text-accent animate-pulse">
                    Generating report &amp; analytics…
                  </span>
                )}
                {!['completed', 'cancelled', 'failed', 'generating_report'].includes(
                  currentSimulation.status
                ) && (
                  <Button
                    variant="danger"
                    leftIcon={<Square className="w-4 h-4" />}
                    isLoading={controlLoading === 'stop'}
                    disabled={controlLoading !== null}
                    onClick={() => handleControl('stop')}
                  >
                    End
                  </Button>
                )}
            </div>
          </div>
        </div>

        <div className="w-full lg:w-80 border-b lg:border-b-0 lg:border-l border-slate-700 bg-slate-800/30 overflow-y-auto order-1 lg:order-2 max-h-48 lg:max-h-none">
          <div className="p-3 md:p-4 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-200">Agents</h3>
              <span className="ml-auto text-sm text-slate-400">
                {currentSimulation.agents?.length ?? 0}
              </span>
            </div>
          </div>
          <div className="p-3 md:p-4 space-y-3">
            {(currentSimulation.agents ?? []).length > 0 ? (
              currentSimulation.agents!.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isSelected={selectedAgentId === agent.id}
                  onClick={() => setSelectedAgentId(agent.id)}
                />
              ))
            ) : (
              <p className="text-sm text-slate-500 text-center py-4">No agents yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
