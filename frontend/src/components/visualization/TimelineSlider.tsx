'use client';

import React, { useState, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Star,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { BookmarkData, TimelineEventType } from '@/lib/types';

interface TimelineSliderProps {
  totalRounds: number;
  currentRound: number;
  onRoundChange: (round: number) => void;
  bookmarks?: BookmarkData[];
  onBookmarkToggle?: (round: number) => void;
  keyEvents?: Array<{
    round: number;
    type: TimelineEventType;
    description: string;
  }>;
  className?: string;
}

const eventTypeIcons: Record<TimelineEventType, string> = {
  decision: 'D',
  vote: 'V',
  statement: 'S',
  coalition: 'C',
  conflict: '!',
  agreement: 'A',
};

const eventTypeColors: Record<TimelineEventType, string> = {
  decision: '#3b82f6',
  vote: '#8b5cf6',
  statement: '#64748b',
  coalition: '#22c55e',
  conflict: '#ef4444',
  agreement: '#14b8a6',
};

export function TimelineSlider({
  totalRounds,
  currentRound,
  onRoundChange,
  bookmarks = [],
  onBookmarkToggle,
  keyEvents = [],
  className,
}: TimelineSliderProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [hoveredRound, setHoveredRound] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    content: React.ReactNode;
  }>({ visible: false, x: 0, y: 0, content: null });
  
  const timelineRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const currentRoundRef = useRef(currentRound);
  useEffect(() => {
    currentRoundRef.current = currentRound;
  }, [currentRound]);

  // Playback control
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        const next = currentRoundRef.current + 1;
        if (next > totalRounds) {
          setIsPlaying(false);
          return;
        }
        onRoundChange(next);
      }, 2000 / playbackSpeed);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, totalRounds, onRoundChange]);

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleStepBackward = () => {
    if (currentRound > 1) {
      onRoundChange(currentRound - 1);
    }
  };

  const handleStepForward = () => {
    if (currentRound < totalRounds) {
      onRoundChange(currentRound + 1);
    }
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const round = Math.max(1, Math.min(totalRounds, Math.round(percentage * totalRounds)));
    onRoundChange(round);
  };

  const isBookmarked = (round: number) => {
    return bookmarks.some((b) => b.round === round);
  };

  const getEventsForRound = (round: number) => {
    return keyEvents.filter((e) => e.round === round);
  };

  const handleRoundHover = (
    e: React.MouseEvent,
    round: number
  ) => {
    const events = getEventsForRound(round);
    const bookmark = bookmarks.find((b) => b.round === round);
    
    if (events.length > 0 || bookmark) {
      setTooltip({
        visible: true,
        x: e.clientX,
        y: e.clientY - 80,
        content: (
          <div className="space-y-2 min-w-[200px]">
            <div className="font-semibold text-slate-200">Round {round}</div>
            {bookmark && (
              <div className="flex items-center gap-2 text-amber-400 text-sm">
                <Star className="w-3 h-3 fill-current" />
                <span>{bookmark.label}</span>
              </div>
            )}
            {events.length > 0 && (
              <div className="space-y-1">
                {events.map((event, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <span
                      className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold"
                      style={{
                        backgroundColor: `${eventTypeColors[event.type]}20`,
                        color: eventTypeColors[event.type],
                      }}
                    >
                      {eventTypeIcons[event.type]}
                    </span>
                    <span className="text-slate-300 truncate">{event.description}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ),
      });
    }
  };

  const handleRoundLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  return (
    <div className={clsx('bg-slate-800/50 border border-slate-700 rounded-lg p-4', className)}>
      {/* Controls Row */}
      <div className="flex items-center justify-between mb-4">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleStepBackward}
            disabled={currentRound <= 1}
            className="p-2 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          
          <button
            onClick={handlePlayPause}
            className="p-2 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors"
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          
          <button
            onClick={handleStepForward}
            disabled={currentRound >= totalRounds}
            className="p-2 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SkipForward className="w-4 h-4" />
          </button>

          <div className="ml-4 text-sm text-slate-400">
            Round <span className="text-slate-200 font-semibold">{currentRound}</span>
            {' / '}
            <span className="text-slate-400">{totalRounds}</span>
          </div>
        </div>

        {/* Speed Control */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Speed:</span>
          {[1, 2, 4].map((speed) => (
            <button
              key={speed}
              onClick={() => setPlaybackSpeed(speed)}
              className={clsx(
                'px-2 py-1 rounded text-xs font-medium transition-colors',
                playbackSpeed === speed
                  ? 'bg-accent text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              )}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Track */}
      <div
        ref={timelineRef}
        className="relative h-12 bg-slate-900/50 rounded-lg cursor-pointer select-none"
        onClick={handleTimelineClick}
      >
        {/* Progress Bar */}
        <div
          className="absolute top-0 left-0 h-full bg-accent/20 rounded-l-lg transition-all duration-300"
          style={{ width: `${((currentRound - 1) / (totalRounds - 1)) * 100}%` }}
        />

        {/* Round Markers */}
        <div className="absolute inset-0 flex items-center px-2">
          {Array.from({ length: totalRounds }, (_, i) => i + 1).map((round) => {
            const isActive = round === currentRound;
            const isPast = round < currentRound;
            const events = getEventsForRound(round);
            const hasEvents = events.length > 0;
            const bookmarked = isBookmarked(round);
            const position = ((round - 1) / (totalRounds - 1)) * 100;

            return (
              <div
                key={round}
                className="absolute transform -translate-x-1/2"
                style={{ left: `${position}%` }}
                onMouseEnter={(e) => handleRoundHover(e, round)}
                onMouseLeave={handleRoundLeave}
              >
                {/* Event indicators */}
                {hasEvents && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 flex gap-0.5">
                    {events.slice(0, 2).map((event, idx) => (
                      <div
                        key={idx}
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: eventTypeColors[event.type] }}
                      />
                    ))}
                  </div>
                )}

                {/* Bookmark indicator */}
                {bookmarked && (
                  <div className="absolute -top-5 left-1/2 transform -translate-x-1/2">
                    <Star className="w-3 h-3 text-amber-400 fill-current" />
                  </div>
                )}

                {/* Round marker */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRoundChange(round);
                  }}
                  className={clsx(
                    'w-3 h-3 rounded-full border-2 transition-all duration-200',
                    isActive
                      ? 'bg-accent border-accent scale-125'
                      : isPast
                      ? 'bg-slate-600 border-slate-600'
                      : 'bg-slate-800 border-slate-600 hover:border-slate-500'
                  )}
                />

                {/* Round number (show every 5th or first/last) */}
                {(round === 1 || round === totalRounds || round % 5 === 0) && (
                  <span
                    className={clsx(
                      'absolute top-4 left-1/2 transform -translate-x-1/2 text-xs transition-colors',
                      isActive ? 'text-accent font-medium' : 'text-slate-500'
                    )}
                  >
                    {round}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Current position indicator */}
        <div
          className="absolute top-0 w-1 h-full bg-accent shadow-lg shadow-accent/50 transition-all duration-300"
          style={{ left: `${((currentRound - 1) / (totalRounds - 1)) * 100}%` }}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-6 text-xs">
        <span className="text-slate-500">Event Types:</span>
        {Object.entries(eventTypeIcons).map(([type, icon]) => (
          <div key={type} className="flex items-center gap-1">
            <span
              className="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              style={{
                backgroundColor: `${eventTypeColors[type as TimelineEventType]}20`,
                color: eventTypeColors[type as TimelineEventType],
              }}
            >
              {icon}
            </span>
            <span className="text-slate-400 capitalize">{type}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 ml-4">
          <Star className="w-3 h-3 text-amber-400 fill-current" />
          <span className="text-slate-400">Bookmarked</span>
        </div>
      </div>

      {/* Tooltip */}
      {tooltip.visible && (
        <div
          className="fixed z-50 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.content}
        </div>
      )}
    </div>
  );
}

export default TimelineSlider;
