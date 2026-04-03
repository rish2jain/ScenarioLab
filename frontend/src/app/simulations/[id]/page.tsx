'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Play,
  Pause,
  Square,
  FastForward,
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
  Scale,
  TrendingUp,
  Shield,
  BarChart3,
  Network,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { RoundIndicator } from '@/components/simulation/RoundIndicator';
import { SimulationFeed } from '@/components/simulation/SimulationFeed';
import { AgentCard } from '@/components/simulation/AgentCard';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { Simulation, Agent } from '@/lib/types';


export default function SimulationMonitorPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const {
    currentSimulation,
    setCurrentSimulation,
    agentMessages,
    setAgentMessages,
  } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [simulationSpeed, setSimulationSpeed] = useState(1);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      const [simulationData, messagesData] = await Promise.all([
        api.getSimulation(simulationId),
        api.getAgentMessages(simulationId),
      ]);
      
      if (simulationData) {
        setCurrentSimulation(simulationData);
      }
      setAgentMessages(messagesData);
      setIsLoading(false);
    };

    loadSimulation();
  }, [simulationId, setCurrentSimulation, setAgentMessages]);

  const handleControl = async (action: 'start' | 'pause' | 'resume' | 'stop') => {
    try {
      await api.controlSimulation(simulationId, action);
      // Update local state optimistically
      const statusMap: Record<string, Simulation['status']> = {
        start: 'running',
        pause: 'paused',
        resume: 'running',
        stop: 'completed',
      };
      if (currentSimulation) {
        setCurrentSimulation({
          ...currentSimulation,
          status: statusMap[action],
        });
      }
    } catch (error) {
      console.error('Control action failed:', error);
    }
  };

  const formatElapsedTime = (seconds?: number) => {
    if (!seconds) return '00:00:00';
    const hrs = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const mins = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${hrs}:${mins}:${secs}`;
  };

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading simulation...</div>
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
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-slate-400">
              <Clock className="w-4 h-4" />
              <span className="font-mono">
                {formatElapsedTime(currentSimulation.elapsedTime)}
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
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {currentSimulation.status === 'running' ? (
                  <Button
                    variant="secondary"
                    leftIcon={<Pause className="w-4 h-4" />}
                    onClick={() => handleControl('pause')}
                  >
                    Pause
                  </Button>
                ) : currentSimulation.status === 'paused' ? (
                  <Button
                    leftIcon={<Play className="w-4 h-4" />}
                    onClick={() => handleControl('resume')}
                  >
                    Resume
                  </Button>
                ) : currentSimulation.status === 'pending' ? (
                  <Button
                    leftIcon={<Play className="w-4 h-4" />}
                    onClick={() => handleControl('start')}
                  >
                    Start
                  </Button>
                ) : null}
                
                {currentSimulation.status !== 'completed' && (
                  <Button
                    variant="danger"
                    leftIcon={<Square className="w-4 h-4" />}
                    onClick={() => handleControl('stop')}
                  >
                    End
                  </Button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Speed:</span>
                {[0.5, 1, 2, 4].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => setSimulationSpeed(speed)}
                    className={`px-2 py-1 rounded text-sm font-medium transition-colors ${
                      simulationSpeed === speed
                        ? 'bg-accent text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
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
