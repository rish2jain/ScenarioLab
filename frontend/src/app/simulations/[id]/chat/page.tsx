'use client';

import { useEffect, useLayoutEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Send, User, Bot } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { useToast } from '@/components/ui/Toast';
import { useChatStore, useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import { archetypeColors } from '@/lib/archetypeColors';
import type { ChatMessage, AgentArchetype } from '@/lib/types';

// Agent type for chat page
interface ChatAgent {
  id: string;
  name: string;
  role: string;
  archetype: AgentArchetype;
  color?: string;
  traits?: string[];
}

const DEFAULT_CHAT_AGENT_COLOR = '#6b7280';

/** UUID v4 when `randomUUID` is missing (non-secure or legacy browsers). */
function randomUUIDCompat(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6]! & 0x0f) | 0x40;
    bytes[8] = (bytes[8]! & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `fallback-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function createChatMessageId(): string {
  return `msg-${randomUUIDCompat()}`;
}

export default function ChatPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { messages, setMessages, selectedAgentId, setSelectedAgentId, addMessage } = useChatStore();
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  const { addToast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [simNotFound, setSimNotFound] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [agents, setAgents] = useState<ChatAgent[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load draft before passive effects: if this were useEffect, the debounced save
  // below would run first with inputMessage '' and removeItem the key we are about
  // to hydrate (first-mount regression).
  useLayoutEffect(() => {
    if (!simulationId) return;
    const draft = localStorage.getItem(`chat_draft_${simulationId}`);
    setInputMessage(draft ?? '');
  }, [simulationId]);

  // Save draft to local storage (debounced)
  useEffect(() => {
    if (!simulationId) return;
    if (!inputMessage) {
      localStorage.removeItem(`chat_draft_${simulationId}`);
      return;
    }
    const timer = setTimeout(() => {
      localStorage.setItem(`chat_draft_${simulationId}`, inputMessage);
    }, 400);
    return () => clearTimeout(timer);
  }, [inputMessage, simulationId]);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        if (!simulationId) {
          return;
        }

        const simulationData = await api.getSimulation(simulationId);

        if (simulationData === null) {
          setCurrentSimulation(null);
          setSimNotFound(true);
          setLoadError(null);
          setMessages([]);
          setAgents([]);
          return;
        }

        setCurrentSimulation(simulationData);
        setSimNotFound(false);
        setLoadError(null);

        const [messagesData, agentsData] = await Promise.all([
          api.getChatMessages(simulationId),
          api.getSimulationAgents(simulationId),
        ]);

        setMessages(messagesData);

        if (agentsData && agentsData.length > 0) {
          setAgents(
            agentsData.map((a) => ({
              id: a.id,
              name: a.name,
              role: a.role,
              archetype: a.archetype as AgentArchetype,
              color: archetypeColors[a.archetype] || '#6b7280',
            }))
          );
        } else {
          setAgents([]);
        }
      } catch (error) {
        setCurrentSimulation(null);
        setSimNotFound(false);
        setLoadError(
          error instanceof Error
            ? error.message
            : 'Could not load this simulation. Check your connection and that the backend is running.'
        );
        setMessages([]);
        setAgents([]);
      } finally {
        setIsLoading(false);
      }
    };

    void loadData();
  }, [simulationId, setCurrentSimulation, setMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const outboundMessage = inputMessage.trim();
    const previousMessages = messages;
    setIsSending(true);
    
    // Add user message
    const userMessage: ChatMessage = {
      id: createChatMessageId(),
      simulationId,
      content: outboundMessage,
      timestamp: new Date().toISOString(),
      isUser: true,
    };
    addMessage(userMessage);
    setInputMessage('');
    localStorage.removeItem(`chat_draft_${simulationId}`);

    try {
      // Send to API and get response
      if (selectedAgentId) {
        const response = await api.sendAgentChat(
          simulationId,
          selectedAgentId,
          outboundMessage
        );

        const content =
          typeof response?.response === 'string' ? response.response : '';
        const resolvedAgentId =
          (typeof response?.agent_id === 'string' && response.agent_id.trim())
            ? response.agent_id.trim()
            : selectedAgentId;

        if (!resolvedAgentId || !content.trim()) {
          console.warn(
            '[ChatPage] sendAgentChat: missing agent_id or response text; skipping addMessage',
            { response, selectedAgentId }
          );
          addToast('The agent did not return a valid reply.', 'error');
          return;
        }

        const agentRow = agents.find((a) => a.id === resolvedAgentId);
        const agentMessage: ChatMessage = {
          id: createChatMessageId(),
          simulationId,
          agentId: resolvedAgentId,
          agentName:
            (typeof response?.agent_name === 'string' && response.agent_name.trim())
              ? response.agent_name.trim()
              : agentRow?.name ?? 'Agent',
          agentColor: agentRow?.color ?? DEFAULT_CHAT_AGENT_COLOR,
          content,
          timestamp:
            typeof response?.timestamp === 'string' && response.timestamp.trim()
              ? response.timestamp
              : new Date().toISOString(),
          isUser: false,
        };
        addMessage(agentMessage);
      } else {
        const response = await api.sendChatMessage(
          simulationId,
          outboundMessage,
          undefined
        );
        addMessage(response);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(previousMessages);
      setInputMessage(outboundMessage);
      localStorage.setItem(`chat_draft_${simulationId}`, outboundMessage);
      addToast(
        error instanceof Error ? error.message : 'Failed to send message.',
        'error'
      );
    } finally {
      setIsSending(false);
    }
  };

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading chat...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 px-4 text-center">
        <div className="text-red-400 max-w-md">{loadError}</div>
        <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
          Retry
        </Button>
        <Link href={`/simulations/${simulationId}`}>
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back to simulation
          </Button>
        </Link>
      </div>
    );
  }

  if (simNotFound) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 px-4 text-center">
        <div className="text-slate-400">Simulation not found</div>
        <Link href="/simulations">
          <Button variant="secondary" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back to simulations
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 md:gap-4 min-w-0">
            <Link href={`/simulations/${simulationId}`}>
              <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
                Back
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-base md:text-xl font-bold text-slate-100 truncate">
                Post-Simulation Chat
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                {currentSimulation?.name}
              </p>
            </div>
          </div>
          <Badge variant="info" className="hidden sm:inline-flex">Post-simulation</Badge>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Agent Selector */}
        <div className="w-full md:w-72 border-b md:border-b-0 md:border-r border-slate-700 bg-slate-800/30 overflow-y-auto max-h-40 md:max-h-none flex-shrink-0">
          <div className="p-4 border-b border-slate-700">
            <h3 className="font-semibold text-slate-200">Select Agent</h3>
            <p className="text-xs text-slate-400 mt-1">
              Choose an agent to chat with
            </p>
          </div>
          <div className="p-3 space-y-2">
            <button
              onClick={() => setSelectedAgentId(null)}
              className={`w-full p-3 rounded-lg border text-left transition-all ${
                selectedAgentId === null
                  ? 'border-accent bg-accent/10'
                  : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                  <User className="w-5 h-5 text-slate-400" />
                </div>
                <div>
                  <p className="font-medium text-slate-200">All Agents</p>
                  <p className="text-xs text-slate-400">Group discussion</p>
                </div>
              </div>
            </button>

            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgentId(agent.id)}
                className={`w-full p-3 rounded-lg border text-left transition-all ${
                  selectedAgentId === agent.id
                    ? 'border-accent bg-accent/10'
                    : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                    style={{ backgroundColor: `${agent.color || '#6b7280'}20`, color: agent.color || '#6b7280' }}
                  >
                    {agent.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-200 truncate">{agent.name}</p>
                    <p className="text-xs text-slate-400 truncate">{agent.role}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Agent Info */}
          {selectedAgent && (
            <div className="px-6 py-3 border-b border-slate-700 bg-slate-800/30">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                  style={{ backgroundColor: `${selectedAgent.color}20`, color: selectedAgent.color }}
                >
                  {selectedAgent.name.charAt(0)}
                </div>
                <div>
                  <p className="font-semibold text-slate-200">{selectedAgent.name}</p>
                  <p className="text-sm text-slate-400">{selectedAgent.role}</p>
                </div>
                <div className="ml-auto">
                  <Badge variant="default" size="sm">
                    {selectedAgent.archetype}
                  </Badge>
                </div>
              </div>
              {selectedAgent.traits && selectedAgent.traits.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {selectedAgent.traits.map((trait, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <Bot className="w-12 h-12 mb-4 opacity-50" />
                <p>Start a conversation with the agents</p>
                <p className="text-sm mt-1">
                  Ask questions about the simulation or explore alternative scenarios
                </p>
              </div>
            )}
            
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] ${
                    message.isUser ? 'flex-row-reverse' : 'flex-row'
                  } flex gap-3`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold ${
                      message.isUser
                        ? 'bg-accent text-white'
                        : 'bg-slate-700'
                    }`}
                    style={
                      !message.isUser && message.agentColor
                        ? { backgroundColor: `${message.agentColor}20`, color: message.agentColor }
                        : {}
                    }
                  >
                    {message.isUser ? (
                      <User className="w-4 h-4" />
                    ) : (
                      message.agentName?.charAt(0) || 'A'
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={`rounded-2xl px-4 py-2 ${
                      message.isUser
                        ? 'bg-accent text-white rounded-br-none'
                        : 'bg-slate-700 text-slate-200 rounded-bl-none'
                    }`}
                  >
                    {!message.isUser && message.agentName && (
                      <p className="text-xs font-medium opacity-70 mb-1">
                        {message.agentName}
                      </p>
                    )}
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <p
                      className={`text-xs mt-1 ${
                        message.isUser ? 'text-accent-light/70' : 'text-slate-500'
                      }`}
                    >
                      {formatTime(message.timestamp)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            
            {isSending && (
              <div
                className="flex justify-start"
                role="status"
                aria-live="polite"
              >
                <span className="sr-only">Agent is typing</span>
                <div className="flex gap-3" aria-hidden="true">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-slate-400" />
                  </div>
                  <div className="bg-slate-700 rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5 h-10 mt-auto">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-4 md:px-6 py-3 md:py-4 border-t border-slate-700 bg-slate-800/50">
            <div className="flex gap-2 md:gap-3">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder={`Message ${selectedAgent?.name || 'all agents'}...`}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                isLoading={isSending}
                leftIcon={<Send className="w-4 h-4" />}
                className="flex-shrink-0"
              >
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
