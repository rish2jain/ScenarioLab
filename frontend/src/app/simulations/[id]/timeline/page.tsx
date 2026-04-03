'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Star, Download, Users, Share2, TrendingUp } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { TimelineSlider } from '@/components/visualization/TimelineSlider';
import { TimelineEvent } from '@/components/visualization/TimelineEvent';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type {
  Simulation,
  TimelineEvent as TimelineEventType,
  TimelineRound,
  BookmarkData,
  TimelineEventType as EventType,
} from '@/lib/types';

// Mock data generator
function generateMockTimelineData(totalRounds: number): TimelineRound[] {
  const eventTypes: EventType[] = ['decision', 'vote', 'statement', 'coalition', 'conflict', 'agreement'];
  const agentNames = ['Sarah Chen', 'Michael Torres', 'Jennifer Walsh', 'David Park', 'Emma Wilson', 'James Liu'];
  const agentRoles = ['Acquiring CEO', 'Target CEO', 'Integration Lead', 'HR Director', 'Board Member', 'Legal Counsel'];
  const agentColors = ['#14b8a6', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', '#22c55e'];
  
  const rounds: TimelineRound[] = [];
  
  for (let round = 1; round <= totalRounds; round++) {
    const eventCount = Math.floor(Math.random() * 3) + 3; // 3-5 events per round
    const events: TimelineEventType[] = [];
    
    for (let i = 0; i < eventCount; i++) {
      const agentIdx = Math.floor(Math.random() * agentNames.length);
      events.push({
        id: `event-${round}-${i}`,
        round,
        timestamp: new Date(Date.now() - (totalRounds - round) * 3600000 - i * 60000).toISOString(),
        agentId: `agent-${agentIdx + 1}`,
        agentName: agentNames[agentIdx],
        agentRole: agentRoles[agentIdx],
        agentColor: agentColors[agentIdx],
        type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
        content: getRandomEventContent(eventTypes[Math.floor(Math.random() * eventTypes.length)]),
        importance: ['low', 'medium', 'high', 'critical'][Math.floor(Math.random() * 4)] as TimelineEventType['importance'],
        relatedAgents: Math.random() > 0.5 
          ? [`agent-${(agentIdx + 1) % agentNames.length + 1}`, `agent-${(agentIdx + 2) % agentNames.length + 1}`]
          : undefined,
      });
    }
    
    rounds.push({
      round,
      events,
      summary: `Round ${round} focused on key strategic decisions and stakeholder alignment.`,
      activeCoalitions: ['Pro-Merger', 'Integration Team'],
      agentStances: {
        'agent-1': Math.floor(Math.random() * 100) - 50,
        'agent-2': Math.floor(Math.random() * 100) - 50,
        'agent-3': Math.floor(Math.random() * 100) - 50,
      },
    });
  }
  
  return rounds;
}

function getRandomEventContent(type: EventType): string {
  const contents: Record<EventType, string[]> = {
    decision: [
      'We have decided to proceed with the phased integration approach.',
      'The board has approved the retention package for key personnel.',
      'Leadership has committed to a 90-day timeline for core systems integration.',
    ],
    vote: [
      'Motion to delay the merger announcement passes 5-3.',
      'The committee voted unanimously to approve the cultural assessment.',
      'Proposal for immediate cost-cutting measures rejected 4-4.',
    ],
    statement: [
      'I believe we need to carefully consider the employee impact before proceeding.',
      'Our priority must be maintaining customer confidence during this transition.',
      'The data suggests we are underestimating the integration complexity.',
    ],
    coalition: [
      'The integration team and HR directors have formed a joint working group.',
      'Several board members have aligned on a conservative approach to the merger.',
      'Operations and IT leadership have agreed to collaborate on systems planning.',
    ],
    conflict: [
      'Disagreement emerged regarding the timeline for workforce reductions.',
      'Tensions rose over allocation of budget between departments.',
      'Conflicting priorities between speed of integration and cultural preservation.',
    ],
    agreement: [
      'All parties agreed on the need for transparent communication.',
      'Consensus reached on the phased approach to systems integration.',
      'Leadership aligned on prioritizing customer retention during transition.',
    ],
  };
  
  const options = contents[type];
  return options[Math.floor(Math.random() * options.length)];
}

export default function TimelinePage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [currentRound, setCurrentRound] = useState(1);
  const [timelineData, setTimelineData] = useState<TimelineRound[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkData[]>([]);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      const simulationData = await api.getSimulation(simulationId);
      
      if (simulationData) {
        setCurrentSimulation(simulationData);
        setCurrentRound(simulationData.currentRound || 1);
        setTimelineData(generateMockTimelineData(simulationData.totalRounds));
        
        // Add some initial bookmarks
        setBookmarks([
          {
            id: 'bookmark-1',
            round: 3,
            label: 'Critical Decision Point',
            note: 'Board approved the integration timeline',
            createdAt: new Date().toISOString(),
          },
          {
            id: 'bookmark-2',
            round: 7,
            label: 'Coalition Formed',
            note: 'Key stakeholders aligned on approach',
            createdAt: new Date().toISOString(),
          },
        ]);
      }
      setIsLoading(false);
    };

    loadSimulation();
  }, [simulationId, setCurrentSimulation]);

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
          description: e.content.slice(0, 50) + '...',
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
          onBookmarkToggle={handleBookmarkToggle}
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
