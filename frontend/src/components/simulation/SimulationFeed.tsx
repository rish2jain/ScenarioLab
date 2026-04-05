'use client';

import { useEffect, useRef, memo } from 'react';
import { clsx } from 'clsx';
import type { AgentMessage } from '@/lib/types';

const getContrastTextColor = (bgColor?: string): string => {
  if (!bgColor || !bgColor.startsWith('#')) return '#ffffff';
  const hex = bgColor.replace('#', '');
  const r = parseInt(hex.length === 3 ? hex.charAt(0) + hex.charAt(0) : hex.slice(0, 2), 16);
  const g = parseInt(hex.length === 3 ? hex.charAt(1) + hex.charAt(1) : hex.slice(2, 4), 16);
  const b = parseInt(hex.length === 3 ? hex.charAt(2) + hex.charAt(2) : hex.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return '#ffffff';
  const luma = 0.299 * r + 0.587 * g + 0.114 * b;
  return luma > 128 ? '#111827' : '#ffffff';
};

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
      aria-live="polite"
      aria-relevant="additions"
    >
      {Object.entries(groupedMessages).map(([round, roundMessages]) => (
        <div key={round} className="space-y-3">
          {/* Round Header */}
          <div className="flex items-center gap-4" role="separator" aria-label={`Round ${round}`}>
            <div className="flex-1 h-px bg-border" />
            <span className="px-3 py-1 bg-background-secondary rounded-full text-xs font-medium text-foreground-muted border border-border">
              Round {round}
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* Messages */}
          {roundMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-3 animate-fade-in"
            >
              {/* Avatar */}
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold shadow-sm"
                style={{ backgroundColor: message.agentColor, color: getContrastTextColor(message.agentColor) }}
              >
                {(message.agentName ?? '?').charAt(0)}
              </div>

              {/* Message Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-foreground">
                    {message.agentName}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded text-xs font-medium border"
                    style={{ borderColor: message.agentColor, color: message.agentColor }}
                  >
                    {message.agentRole}
                  </span>
                  <time dateTime={message.timestamp} className="text-xs text-foreground-subtle">
                    {formatTime(message.timestamp)}
                  </time>
                  {getMessageTypeIcon(message.type) && (
                    <span className="text-xs text-foreground-subtle">
                      {getMessageTypeIcon(message.type)}
                    </span>
                  )}
                </div>
                <div className="text-foreground-muted leading-relaxed font-sans"><MessageContent content={message.content} /></div>
              </div>
            </div>
          ))}
        </div>
      ))}

      {messages.length === 0 && (
        <div className="flex items-center justify-center h-32 text-foreground-subtle">
          No messages yet. Simulation will begin shortly.
        </div>
      )}
    </div>
  );
}

/**
 * Minimal inline markup for simulation messages (not a full Markdown engine).
 *
 * Supported per line only. Alternation order matches the split regex: `**bold**`,
 * `*italic*` (single-asterisk pairs), `` `code` ``. Spans must not overlap or nest;
 * nested or malformed markup is not handled. Plain text passes through; unsupported
 * Markdown (links, lists, block syntax) is shown as literal text.
 */
const MessageContent = memo(function MessageContent({
  content,
}: {
  content: string;
}) {
  const renderedContent = content.split('\n').map((line, lineIdx) => {
    // Split on: **...**, *...* (single asterisks, not **), `...` — see JSDoc above.
    const parts = line.split(/(\*\*.*?\*\*|\*[^*]+\*|`[^`]+`)/g);
    return (
      <span key={lineIdx} className="block min-h-[1.5rem]">
        {parts.map((part, partIdx) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={partIdx} className="font-bold text-foreground">
                {part.slice(2, -2)}
              </strong>
            );
          } else if (part.startsWith('*') && part.endsWith('*')) {
            return (
              <em key={partIdx} className="italic text-foreground-muted">
                {part.slice(1, -1)}
              </em>
            );
          } else if (part.startsWith('`') && part.endsWith('`')) {
            return (
              <code
                key={partIdx}
                className="bg-background-tertiary text-accent font-mono px-1 py-0.5 rounded text-sm"
              >
                {part.slice(1, -1)}
              </code>
            );
          }
          return <span key={partIdx}>{part}</span>;
        })}
      </span>
    );
  });

  return <>{renderedContent}</>;
});
