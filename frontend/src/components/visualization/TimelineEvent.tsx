'use client';

import React from 'react';
import { clsx } from 'clsx';
import {
  Gavel,
  Vote,
  MessageSquare,
  Users,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Hash,
} from 'lucide-react';
import type { TimelineEvent as TimelineEventType } from '@/lib/types';

interface TimelineEventProps {
  event: TimelineEventType;
  className?: string;
  onClick?: () => void;
  isHighlighted?: boolean;
}

const eventTypeConfig = {
  decision: {
    icon: Gavel,
    label: 'Decision',
    color: '#3b82f6',
    bgColor: 'rgba(59, 130, 246, 0.15)',
    borderColor: 'rgba(59, 130, 246, 0.3)',
  },
  vote: {
    icon: Vote,
    label: 'Vote',
    color: '#8b5cf6',
    bgColor: 'rgba(139, 92, 246, 0.15)',
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  statement: {
    icon: MessageSquare,
    label: 'Statement',
    color: '#64748b',
    bgColor: 'rgba(100, 116, 139, 0.15)',
    borderColor: 'rgba(100, 116, 139, 0.3)',
  },
  coalition: {
    icon: Users,
    label: 'Coalition',
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.15)',
    borderColor: 'rgba(34, 197, 94, 0.3)',
  },
  conflict: {
    icon: AlertTriangle,
    label: 'Conflict',
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
  },
  agreement: {
    icon: CheckCircle2,
    label: 'Agreement',
    color: '#14b8a6',
    bgColor: 'rgba(20, 184, 166, 0.15)',
    borderColor: 'rgba(20, 184, 166, 0.3)',
  },
};

const importanceConfig = {
  low: {
    indicator: 'bg-slate-600',
    label: 'Low',
  },
  medium: {
    indicator: 'bg-blue-500',
    label: 'Medium',
  },
  high: {
    indicator: 'bg-amber-500',
    label: 'High',
  },
  critical: {
    indicator: 'bg-red-500',
    label: 'Critical',
  },
};

export function TimelineEvent({
  event,
  className,
  onClick,
  isHighlighted = false,
}: TimelineEventProps) {
  const config = eventTypeConfig[event.type];
  const Icon = config.icon;
  const importance = importanceConfig[event.importance];

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      onClick={onClick}
      className={clsx(
        'relative p-4 rounded-lg border transition-all duration-200',
        isHighlighted
          ? 'bg-slate-700/50 border-accent shadow-lg shadow-accent/10'
          : 'bg-slate-800/30 border-slate-700 hover:border-slate-600',
        onClick && 'cursor-pointer',
        className
      )}
      style={{
        borderLeftWidth: '4px',
        borderLeftColor: config.color,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        {/* Agent Info */}
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{
              backgroundColor: `${event.agentColor}20`,
            }}
          >
            <span
              className="text-sm font-bold"
              style={{ color: event.agentColor }}
            >
              {event.agentName.charAt(0)}
            </span>
          </div>
          <div>
            <div className="font-medium text-slate-200">{event.agentName}</div>
            <div className="text-sm text-slate-400">{event.agentRole}</div>
          </div>
        </div>

        {/* Event Type Badge */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
          style={{
            backgroundColor: config.bgColor,
            color: config.color,
          }}
        >
          <Icon className="w-3 h-3" />
          {config.label}
        </div>
      </div>

      {/* Content */}
      <div className="mb-3">
        <p className="text-slate-300 leading-relaxed">{event.content}</p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          {/* Timestamp */}
          <div className="flex items-center gap-1.5 text-slate-500">
            <Clock className="w-3 h-3" />
            <span>{formatTime(event.timestamp)}</span>
          </div>

          {/* Round */}
          <div className="flex items-center gap-1.5 text-slate-500">
            <Hash className="w-3 h-3" />
            <span>Round {event.round}</span>
          </div>

          {/* Importance */}
          <div className="flex items-center gap-1.5">
            <div className={clsx('w-2 h-2 rounded-full', importance.indicator)} />
            <span className="text-slate-500">{importance.label}</span>
          </div>
        </div>

        {/* Related Agents */}
        {event.relatedAgents && event.relatedAgents.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Related:</span>
            <div className="flex -space-x-1">
              {event.relatedAgents.slice(0, 3).map((agentId, idx) => (
                <div
                  key={agentId}
                  className="w-5 h-5 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-[10px] text-slate-400"
                >
                  {String.fromCharCode(65 + idx)}
                </div>
              ))}
              {event.relatedAgents.length > 3 && (
                <div className="w-5 h-5 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-[10px] text-slate-400">
                  +{event.relatedAgents.length - 3}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Highlight indicator */}
      {isHighlighted && (
        <div className="absolute -left-1 top-1/2 transform -translate-y-1/2 w-2 h-8 bg-accent rounded-r" />
      )}
    </div>
  );
}

// Compact version for smaller displays
export function TimelineEventCompact({
  event,
  className,
  onClick,
}: TimelineEventProps) {
  const config = eventTypeConfig[event.type];
  const Icon = config.icon;

  return (
    <div
      onClick={onClick}
      className={clsx(
        'flex items-center gap-3 p-3 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors cursor-pointer',
        className
      )}
      style={{ borderLeftColor: config.color, borderLeftWidth: '3px' }}
    >
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: `${event.agentColor}20` }}
      >
        <span className="text-xs font-bold" style={{ color: event.agentColor }}>
          {event.agentName.charAt(0)}
        </span>
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-200 text-sm truncate">
            {event.agentName}
          </span>
          <Icon className="w-3 h-3" style={{ color: config.color }} />
        </div>
        <p className="text-xs text-slate-400 truncate">{event.content}</p>
      </div>

      <div className="text-xs text-slate-500">
        R{event.round}
      </div>
    </div>
  );
}

export default TimelineEvent;
