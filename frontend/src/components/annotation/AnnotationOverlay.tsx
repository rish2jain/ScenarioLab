'use client';

import React, { useState } from 'react';
import { clsx } from 'clsx';
import { MessageSquare, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { AnnotationMarker } from './AnnotationMarker';
import { AnnotationPanel } from './AnnotationPanel';
import type { AgentMessage } from '@/lib/types';

interface AnnotationOverlayProps {
  simulationId: string;
  messages: AgentMessage[];
  children?: React.ReactNode;
  className?: string;
  showPanel?: boolean;
  onTogglePanel?: () => void;
}

// Group messages by round
function groupMessagesByRound(messages: AgentMessage[]): Record<number, AgentMessage[]> {
  return messages.reduce((acc, message) => {
    if (!acc[message.round]) {
      acc[message.round] = [];
    }
    acc[message.round].push(message);
    return acc;
  }, {} as Record<number, AgentMessage[]>);
}

export function AnnotationOverlay({
  simulationId,
  messages,
  children,
  className,
  showPanel = false,
  onTogglePanel,
}: AnnotationOverlayProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(showPanel);

  const handleTogglePanel = () => {
    const newState = !isPanelOpen;
    setIsPanelOpen(newState);
    onTogglePanel?.();
  };

  const groupedMessages = groupMessagesByRound(messages);

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

  return (
    <div className={clsx('flex h-full', className)}>
      {/* Main Feed with Annotation Markers */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700 bg-slate-800/30">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <MessageSquare className="w-4 h-4" />
            <span>Annotated Feed</span>
          </div>
          <button
            onClick={handleTogglePanel}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              isPanelOpen
                ? 'bg-accent text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            )}
          >
            {isPanelOpen ? (
              <>
                <PanelRightClose className="w-4 h-4" />
                Hide Panel
              </>
            ) : (
              <>
                <PanelRightOpen className="w-4 h-4" />
                Show Annotations
              </>
            )}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
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

              {/* Messages with Annotation Markers */}
              {roundMessages.map((message) => (
                <div
                  key={message.id}
                  className="group flex gap-3 animate-fade-in"
                >
                  {/* Avatar */}
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold"
                    style={{
                      backgroundColor: `${message.agentColor}20`,
                      color: message.agentColor,
                    }}
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
                        style={{
                          backgroundColor: `${message.agentColor}20`,
                          color: message.agentColor,
                        }}
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
                      
                      {/* Annotation Marker */}
                      <AnnotationMarker
                        messageId={message.id}
                        simulationId={simulationId}
                        roundNumber={message.round}
                      />
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

        {/* Render children if provided */}
        {children}
      </div>

      {/* Annotation Panel */}
      {isPanelOpen && (
        <AnnotationPanel
          simulationId={simulationId}
          className="w-80"
          onClose={handleTogglePanel}
        />
      )}
    </div>
  );
}

// Simpler version that just wraps existing content with annotation capability
interface SimpleAnnotationOverlayProps {
  simulationId: string;
  children: React.ReactNode;
  className?: string;
}

export function SimpleAnnotationOverlay({
  simulationId,
  children,
  className,
}: SimpleAnnotationOverlayProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  return (
    <div className={clsx('flex h-full', className)}>
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-end px-4 py-2 border-b border-slate-700 bg-slate-800/30">
          <button
            onClick={() => setIsPanelOpen(!isPanelOpen)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              isPanelOpen
                ? 'bg-accent text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            )}
          >
            {isPanelOpen ? (
              <>
                <PanelRightClose className="w-4 h-4" />
                Hide Annotations
              </>
            ) : (
              <>
                <PanelRightOpen className="w-4 h-4" />
                Show Annotations
              </>
            )}
          </button>
        </div>
        
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>

      {isPanelOpen && (
        <AnnotationPanel
          simulationId={simulationId}
          className="w-80"
          onClose={() => setIsPanelOpen(false)}
        />
      )}
    </div>
  );
}

export default AnnotationOverlay;
