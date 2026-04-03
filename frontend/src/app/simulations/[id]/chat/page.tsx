'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Send, User, Bot, Clock } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { useChatStore, useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
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

// Agent colors based on archetype
const archetypeColors: Record<string, string> = {
  aggressor: '#14b8a6',
  defender: '#f59e0b',
  mediator: '#3b82f6',
  analyst: '#8b5cf6',
  influencer: '#ec4899',
  skeptic: '#6b7280',
};

// Mock agents for fallback
const mockAgents: ChatAgent[] = [
  {
    id: 'agent-1',
    name: 'Sarah Chen',
    role: 'Acquiring CEO',
    archetype: 'aggressor',
    color: '#14b8a6',
    traits: ['Decisive', 'Results-oriented', 'Direct'],
  },
  {
    id: 'agent-2',
    name: 'Michael Torres',
    role: 'Target CEO',
    archetype: 'defender',
    color: '#f59e0b',
    traits: ['Cautious', 'Empathetic', 'Strategic'],
  },
  {
    id: 'agent-3',
    name: 'Jennifer Walsh',
    role: 'Integration Lead',
    archetype: 'mediator',
    color: '#3b82f6',
    traits: ['Diplomatic', 'Organized', 'Patient'],
  },
  {
    id: 'agent-4',
    name: 'David Park',
    role: 'HR Director',
    archetype: 'analyst',
    color: '#8b5cf6',
    traits: ['Detail-oriented', 'Empathetic', 'Data-driven'],
  },
];

export default function ChatPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { messages, setMessages, selectedAgentId, setSelectedAgentId, addMessage } = useChatStore();
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();

  const [isLoading, setIsLoading] = useState(true);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [agents, setAgents] = useState<ChatAgent[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      const [simulationData, messagesData, agentsData] = await Promise.all([
        api.getSimulation(simulationId),
        api.getChatMessages(simulationId),
        api.getSimulationAgents(simulationId),
      ]);

      if (simulationData) {
        setCurrentSimulation(simulationData);
      }
      setMessages(messagesData);

      // Use real agents if available, otherwise use mock
      if (agentsData && agentsData.length > 0) {
        setAgents(agentsData.map(a => ({
          id: a.id,
          name: a.name,
          role: a.role,
          archetype: a.archetype as AgentArchetype,
          color: archetypeColors[a.archetype] || '#6b7280',
        })));
      } else {
        setAgents(mockAgents);
      }
      setIsLoading(false);
    };

    loadData();
  }, [simulationId, setCurrentSimulation, setMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    setIsSending(true);
    
    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      simulationId,
      content: inputMessage,
      timestamp: new Date().toISOString(),
      isUser: true,
    };
    addMessage(userMessage);
    setInputMessage('');

    try {
      // Send to API and get response
      if (selectedAgentId) {
        const response = await api.sendAgentChat(
          simulationId,
          selectedAgentId,
          inputMessage
        );
        if (response) {
          const agentMessage: ChatMessage = {
            id: `msg-${Date.now()}`,
            simulationId,
            agentId: response.agent_id,
            agentName: response.agent_name,
            agentColor: agents.find(a => a.id === response.agent_id)?.color,
            content: response.response,
            timestamp: response.timestamp,
            isUser: false,
          };
          addMessage(agentMessage);
        }
      } else {
        // No agent selected, use mock response
        const response = await api.sendChatMessage(
          simulationId,
          inputMessage,
          undefined
        );
        addMessage(response);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
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
