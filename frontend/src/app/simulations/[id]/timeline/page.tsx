'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Star, Download, Share2, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import dynamic from 'next/dynamic';

const TimelineSlider = dynamic(
  () => import('@/components/visualization/TimelineSlider').then(mod => ({ default: mod.TimelineSlider })),
  { ssr: false, loading: () => <div className="h-16 animate-pulse bg-zinc-800/50 rounded-lg" /> }
);
const TimelineEvent = dynamic(
  () => import('@/components/visualization/TimelineEvent').then(mod => ({ default: mod.TimelineEvent })),
  { ssr: false }
);
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { TimelineRound, BookmarkData } from '@/lib/types';
import {
  buildTimelineFromMessages,
  mergeSimulationAgentsFromApi,
} from '@/lib/simulation-viz';

const MAX_DESC_LENGTH = 50;

export default function TimelinePage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [currentRound, setCurrentRound] = useState(1);
  const [timelineData, setTimelineData] = useState<TimelineRound[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkData[]>([]);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [simulationData, messagesData, agentRows] = await Promise.all([
          api.getSimulation(simulationId),
          api.getAgentMessages(simulationId),
          api.getSimulationAgents(simulationId),
        ]);

        if (simulationData === null) {
          setCurrentSimulation(null);
          setTimelineData([]);
          setBookmarks([]);
          setError('Simulation not found');
        } else {
          const messagesOk = Array.isArray(messagesData);
          const agentsOk = Array.isArray(agentRows);
          if (!messagesOk || !agentsOk) {
            setCurrentSimulation(null);
            setTimelineData([]);
            setBookmarks([]);
            setError(
              !messagesOk && !agentsOk
                ? 'Could not load simulation messages or agents. Try again later.'
                : !messagesOk
                  ? 'Could not load simulation messages. Try again later.'
                  : 'Could not load simulation agents. Try again later.'
            );
          } else {
            const merged = mergeSimulationAgentsFromApi(simulationData, agentRows);
            setCurrentSimulation(merged);
            setCurrentRound(simulationData.currentRound || 1);
            setTimelineData(buildTimelineFromMessages(merged, messagesData));
            setBookmarks([]);
            setError(null);
          }
        }
      } catch (err) {
        console.error('Timeline load failed', err);
        setCurrentSimulation(null);
        setTimelineData([]);
        setBookmarks([]);
        setError(
          err instanceof Error ? err.message : 'Failed to load timeline data.'
        );
      } finally {
        setIsLoading(false);
      }
    };

    loadSimulation();
  }, [simulationId, setCurrentSimulation, retryKey]);

  const handleRetry = () => {
    setRetryKey((k) => k + 1);
  };

  const currentRoundData = useMemo(() => {
    return timelineData.find((r) => r.round === currentRound);
  }, [timelineData, currentRound]);

  const keyEvents = useMemo(() => {
    return timelineData.flatMap((round) =>
      round.events
        .filter((e) => e.importance === 'high' || e.importance === 'critical')
        .map((e) => ({
          round: round.round,
          type: e.type,
          description:
            e.content.length > MAX_DESC_LENGTH
              ? `${e.content.slice(0, MAX_DESC_LENGTH)}…`
              : e.content,
        }))
    );
  }, [timelineData]);

  const handleBookmarkToggle = (round: number) => {
    setBookmarks((prev) => {
      const exists = prev.find((b) => b.round === round);
      if (exists) {
        return prev.filter((b) => b.round !== round);
      }
      return [
        ...prev,
        {
          id: `bookmark-${Date.now()}`,
          round,
          label: `Bookmark at Round ${round}`,
          createdAt: new Date().toISOString(),
        },
      ];
    });
  };

  const handleExportTimeline = () => {
    const data = {
      simulation: currentSimulation?.name,
      rounds: timelineData,
      bookmarks,
      exportedAt: new Date().toISOString(),
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `timeline-${simulationId}.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading timeline...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 px-4 text-center">
        <div className="text-red-400 max-w-md">{error}</div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Button variant="secondary" size="sm" type="button" onClick={handleRetry}>
            Retry
          </Button>
          <Link href={`/simulations/${simulationId}`}>
            <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Back to simulation
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!currentSimulation) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Simulation not found</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <Link href={`/simulations/${simulationId}`}>
              <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
                Back
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-lg md:text-xl font-bold text-slate-100 truncate">
                Timeline Replay
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                {currentSimulation.name}
              </p>
            </div>
          </div>
          
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Download className="w-4 h-4" />}
            onClick={handleExportTimeline}
          >
            Export Annotated Timeline
          </Button>
        </div>
      </div>

      {/* Timeline Slider */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700">
        <TimelineSlider
          totalRounds={currentSimulation.totalRounds}
          currentRound={currentRound}
          onRoundChange={setCurrentRound}
          bookmarks={bookmarks}
          keyEvents={keyEvents}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Events List */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-200">
                Round {currentRound} Events
              </h2>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">
                  {currentRoundData?.events.length || 0} events
                </span>
                <button
                  onClick={() => handleBookmarkToggle(currentRound)}
                  className={`
                    p-1.5 rounded-lg transition-colors
                    ${bookmarks.some((b) => b.round === currentRound)
                      ? 'text-amber-400 bg-amber-400/10'
                      : 'text-slate-400 hover:text-amber-400 hover:bg-slate-700/50'
                    }
                  `}
                >
                  <Star className={bookmarks.some((b) => b.round === currentRound) ? 'fill-current' : 'w-4 h-4'} />
                </button>
              </div>
            </div>

            <div className="space-y-4">
              {currentRoundData?.events.map((event) => (
                <TimelineEvent
                  key={event.id}
                  event={event}
                />
              ))}
            </div>

            {!currentRoundData?.events.length && (
              <div className="text-center py-12 text-slate-500">
                No events for this round.
              </div>
            )}
          </div>
        </div>

        {/* Side Panel - Round State */}
        <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-slate-700 bg-slate-800/30 overflow-y-auto max-h-64 lg:max-h-none flex-shrink-0">
          <div className="p-4 border-b border-slate-700">
            <h3 className="font-semibold text-slate-200">Round {currentRound} State</h3>
          </div>

          {/* Summary */}
          <div className="p-4 border-b border-slate-700">
            <h4 className="text-sm font-medium text-slate-400 mb-2">Summary</h4>
            <p className="text-sm text-slate-300">
              {currentRoundData?.summary || 'No summary available for this round.'}
            </p>
          </div>

          {/* Active Coalitions */}
          <div className="p-4 border-b border-slate-700">
            <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <Share2 className="w-4 h-4" />
              Active Coalitions
            </h4>
            <div className="space-y-2">
              {currentRoundData?.activeCoalitions.map((coalition) => (
                <div
                  key={coalition}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-700/30 rounded-lg"
                >
                  <div className="w-2 h-2 rounded-full bg-accent" />
                  <span className="text-sm text-slate-300">{coalition}</span>
                </div>
              ))}
              {!currentRoundData?.activeCoalitions.length && (
                <p className="text-sm text-slate-500">No active coalitions</p>
              )}
            </div>
          </div>

          {/* Agent Stances */}
          <div className="p-4 border-b border-slate-700">
            <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Agent Stances
            </h4>
            <div className="space-y-3">
              {currentRoundData?.agentStances && Object.entries(currentRoundData.agentStances).map(([agentId, stance]) => (
                <div key={agentId}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">{agentId.replace('agent-', 'Agent ')}</span>
                    <span className={stance > 0 ? 'text-green-400' : stance < 0 ? 'text-red-400' : 'text-slate-400'}>
                      {stance > 0 ? '+' : ''}{stance}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        stance > 0 ? 'bg-green-500' : stance < 0 ? 'bg-red-500' : 'bg-slate-500'
                      }`}
                      style={{
                        width: `${Math.abs(stance)}%`,
                        marginLeft: stance < 0 ? `${50 - Math.abs(stance) / 2}%` : '50%',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bookmarks List */}
          <div className="p-4">
            <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <Star className="w-4 h-4" />
              Bookmarks
            </h4>
            <div className="space-y-2">
              {bookmarks.map((bookmark) => (
                <button
                  key={bookmark.id}
                  onClick={() => setCurrentRound(bookmark.round)}
                  className="w-full text-left px-3 py-2 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Star className="w-3 h-3 text-amber-400 fill-current" />
                    <span className="text-sm font-medium text-slate-200">{bookmark.label}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Round {bookmark.round}
                  </div>
                  {bookmark.note && (
                    <p className="text-xs text-slate-400 mt-1">{bookmark.note}</p>
                  )}
                </button>
              ))}
              {!bookmarks.length && (
                <p className="text-sm text-slate-500">No bookmarks yet</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
