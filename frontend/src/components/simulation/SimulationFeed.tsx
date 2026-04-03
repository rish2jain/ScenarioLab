'use client';

import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import type { AgentMessage } from '@/lib/types';

interface SimulationFeedProps {
  messages: AgentMessage[];
  className?: string;
}

export function SimulationFeed({ messages, className }: SimulationFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getMessageTypeIcon = (type: AgentMessage['type']) => {
    switch (type) {
      case 'question':
        return '?';
      case 'action':
        return '!';
      case 'response':
        return '↳';
      default:
        return null;
    }
  };

  // Group messages by round
  const groupedMessages = messages.reduce((acc, message) => {
    if (!acc[message.round]) {
      acc[message.round] = [];
    }
    acc[message.round].push(message);
    return acc;
  }, {} as Record<number, AgentMessage[]>);

  return (
    <div
      ref={scrollRef}
      className={clsx(
        'flex-1 overflow-y-auto space-y-6 p-4',
        className
      )}
    >
      {Object.entries(groupedMessages).map(([round, roundMessages]) => (
        <div key={round} className="space-y-3">
          {/* Round Header */}
          <div className="flex items-center gap-4">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="px-3 py-1 bg-slate-800 rounded-full text-xs font-medium text-slate-400 border border-slate-700">
              Round {round}
            </span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>

          {/* Messages */}
          {roundMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-3 animate-fade-in"
            >
              {/* Avatar */}
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold"
                style={{ backgroundColor: `${message.agentColor}20`, color: message.agentColor }}
              >
                {message.agentName.charAt(0)}
              </div>

              {/* Message Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-slate-200">
                    {message.agentName}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded text-xs font-medium"
                    style={{ backgroundColor: `${message.agentColor}20`, color: message.agentColor }}
                  >
                    {message.agentRole}
                  </span>
                  <span className="text-xs text-slate-500">
                    {formatTime(message.timestamp)}
                  </span>
                  {getMessageTypeIcon(message.type) && (
                    <span className="text-xs text-slate-500">
                      {getMessageTypeIcon(message.type)}
                    </span>
                  )}
                </div>
                <p className="text-slate-300 leading-relaxed">{message.content}</p>
              </div>
            </div>
          ))}
        </div>
      ))}

      {messages.length === 0 && (
        <div className="flex items-center justify-center h-32 text-slate-500">
          No messages yet. Simulation will begin shortly.
        </div>
      )}
    </div>
  );
}
