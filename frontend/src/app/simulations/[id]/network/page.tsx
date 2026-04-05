'use client';

import { useEffect, useState, useMemo, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Users, Share2, Filter } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import dynamic from 'next/dynamic';

const NetworkGraph = dynamic(
  () => import('@/components/visualization/NetworkGraph').then(mod => ({ default: mod.NetworkGraph })),
  { ssr: false, loading: () => <div className="h-96 animate-pulse bg-zinc-800/50 rounded-lg" /> }
);
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { NetworkNode, AgentMessage } from '@/lib/types';
import {
  buildNetworkGraphData,
  latestMessageExcerpt,
  mergeSimulationAgentsFromApi,
} from '@/lib/simulation-viz';

export default function NetworkGraphPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();

  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedRound, setSelectedRound] = useState(1);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [isNodeModalOpen, setIsNodeModalOpen] = useState(false);
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const [graphSize, setGraphSize] = useState({ width: 960, height: 720 });
  
  // Filter states
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedCoalitions, setSelectedCoalitions] = useState<string[]>([]);
  const [sentimentThreshold, setSentimentThreshold] = useState(-1);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [simulationData, messagesData, agentRows] = await Promise.all([
          api.getSimulation(simulationId),
          api.getAgentMessages(simulationId),
          api.getSimulationAgents(simulationId),
        ]);

        if (simulationData === undefined) {
          setCurrentSimulation(null);
          setLoadError(
            'Could not load this simulation (API unreachable or server error). Check your connection and that the backend is running.'
          );
        } else if (simulationData === null) {
          setCurrentSimulation(null);
        } else {
          const merged = mergeSimulationAgentsFromApi(simulationData, agentRows);
          setCurrentSimulation(merged);
          setSelectedRound(simulationData.currentRound || 1);
        }
        setAgentMessages(messagesData);
      } catch (error) {
        setCurrentSimulation(null);
        setAgentMessages([]);
        setLoadError(
          error instanceof Error ? error.message : 'Failed to load network data.'
        );
      }
      setIsLoading(false);
    };

    void loadSimulation();
  }, [simulationId, setCurrentSimulation]);

  const networkData = useMemo(() => {
    if (!currentSimulation) return null;
    return buildNetworkGraphData(
      currentSimulation,
      agentMessages,
      selectedRound
    );
  }, [currentSimulation, agentMessages, selectedRound]);

  const selectedTranscript = useMemo(() => {
    if (!selectedNode) return null;
    return latestMessageExcerpt(
      agentMessages,
      selectedNode.id,
      selectedRound
    );
  }, [selectedNode, agentMessages, selectedRound]);

  // Get unique roles and coalitions for filters
  const availableRoles = useMemo(() => {
    if (!networkData) return [];
    return Array.from(new Set(networkData.nodes.map((n) => n.role)));
  }, [networkData]);

  const availableCoalitions = useMemo(() => {
    if (!networkData) return [];
    return Array.from(new Set(networkData.nodes.map((n) => n.coalition).filter(Boolean)));
  }, [networkData]);

  const handleNodeClick = (node: NetworkNode) => {
    setSelectedNode(node);
    setIsNodeModalOpen(true);
  };

  const toggleRole = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  const toggleCoalition = (coalition: string) => {
    setSelectedCoalitions((prev) =>
      prev.includes(coalition) ? prev.filter((c) => c !== coalition) : [...prev, coalition]
    );
  };

  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el) return;

    const updateSize = () => {
      const nextWidth = Math.max(720, Math.floor(el.clientWidth));
      const nextHeight = Math.max(560, Math.floor(el.clientHeight || 720));
      setGraphSize({ width: nextWidth, height: nextHeight });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading network visualization...</div>
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

  if (!currentSimulation || !networkData) {
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
                Agent Network Graph
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                {currentSimulation.name}
              </p>
            </div>
          </div>
          
          {/* Round Selector */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">Round:</span>
            <select
              value={selectedRound}
              onChange={(e) => setSelectedRound(Number(e.target.value))}
              className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50"
            >
              {Array.from({ length: currentSimulation.totalRounds }, (_, i) => i + 1).map((round) => (
                <option key={round} value={round}>
                  Round {round}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Graph Area */}
        <div ref={graphContainerRef} className="flex-1 bg-slate-900/50 overflow-hidden min-w-0 min-h-[560px]">
          <div className="h-full">
            {networkData.nodes.length === 0 ? (
              <div className="flex items-center justify-center h-96 text-slate-400 text-sm px-4 text-center">
                No agents to display for this simulation yet.
              </div>
            ) : (
              <NetworkGraph
                data={networkData}
                width={graphSize.width}
                height={graphSize.height}
                onNodeClick={handleNodeClick}
                selectedNodeId={selectedNode?.id}
                filterRoles={selectedRoles}
                filterCoalitions={selectedCoalitions}
                sentimentThreshold={sentimentThreshold}
                className="w-full h-full"
              />
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-slate-700 bg-slate-800/30 overflow-y-auto max-h-72 lg:max-h-none flex-shrink-0">
          {/* Filters */}
          <div className="p-4 border-b border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-slate-400" />
              <h3 className="font-semibold text-slate-200">Filters</h3>
            </div>

            {/* Role Filter */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                <Users className="w-3 h-3" />
                Roles
              </h4>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {availableRoles.map((role) => (
                  <label
                    key={role}
                    className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-700/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRoles.includes(role)}
                      onChange={() => toggleRole(role)}
                      className="rounded border-slate-600 bg-slate-700 text-accent focus:ring-accent/50"
                    />
                    <span className="text-sm text-slate-300">{role}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Coalition Filter — only when simulation supplies coalition labels */}
            {availableCoalitions.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                  <Share2 className="w-3 h-3" />
                  Coalitions
                </h4>
                <div className="space-y-1">
                  {availableCoalitions.map((coalition) => (
                    <label
                      key={coalition}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-700/50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCoalitions.includes(coalition || '')}
                        onChange={() => toggleCoalition(coalition || '')}
                        className="rounded border-slate-600 bg-slate-700 text-accent focus:ring-accent/50"
                      />
                      <span className="text-sm text-slate-300">{coalition}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Sentiment Threshold */}
            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-2">
                Sentiment Threshold
              </h4>
              <input
                type="range"
                min="-1"
                max="0"
                step="0.1"
                value={sentimentThreshold}
                onChange={(e) => setSentimentThreshold(Number(e.target.value))}
                className="w-full accent-accent"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>Show all</span>
                <span>{sentimentThreshold.toFixed(1)}</span>
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="p-4">
            <h3 className="font-semibold text-slate-200 mb-4">Legend</h3>
            
            {/* Node colors by role */}
            <div className="mb-4">
              <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                Node Size = Authority Level
              </h4>
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full bg-slate-600" />
                <span className="text-sm text-slate-400">Small (Low)</span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <div className="w-6 h-6 rounded-full bg-slate-600" />
                <span className="text-sm text-slate-400">Large (High)</span>
              </div>
            </div>

            {/* Edge colors */}
            <div>
              <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                Edge Colors
              </h4>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-0.5 bg-green-500" />
                  <span className="text-sm text-slate-400">Agreement/Positive</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-0.5 bg-red-500" />
                  <span className="text-sm text-slate-400">Conflict/Negative</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-0.5 bg-slate-500" />
                  <span className="text-sm text-slate-400">Neutral</span>
                </div>
              </div>
            </div>

            {/* Edge thickness */}
            <div className="mt-4">
              <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                Edge Thickness = Message Count
              </h4>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-0.5 bg-slate-500" />
                  <span className="text-sm text-slate-400">Few messages</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-1.5 bg-slate-500" />
                  <span className="text-sm text-slate-400">Many messages</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="p-4 border-t border-slate-700">
            <h3 className="font-semibold text-slate-200 mb-3">Statistics</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Total Agents:</span>
                <span className="text-slate-200">{networkData.nodes.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Connections:</span>
                <span className="text-slate-200">{networkData.edges.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Positive:</span>
                <span className="text-green-400">
                  {networkData.edges.filter((e) => e.sentiment === 'positive').length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Negative:</span>
                <span className="text-red-400">
                  {networkData.edges.filter((e) => e.sentiment === 'negative').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Node Detail Modal */}
      <Modal
        isOpen={isNodeModalOpen}
        onClose={() => setIsNodeModalOpen(false)}
        title={selectedNode?.name}
        description={selectedNode?.role}
      >
        {selectedNode && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold"
                style={{
                  backgroundColor: `${selectedNode.color}20`,
                  color: selectedNode.color,
                }}
              >
                {selectedNode.name.charAt(0)}
              </div>
              <div>
                <div className="text-sm text-slate-400">Archetype</div>
                <div className="text-slate-200 capitalize">{selectedNode.archetype}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                  Authority Level
                </div>
                <div className="text-2xl font-bold text-slate-200">
                  {selectedNode.authorityLevel}/10
                </div>
              </div>
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                  Coalition
                </div>
                <div className="text-lg font-medium text-slate-200">
                  {selectedNode.coalition || 'None'}
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-2">Recent Transcript</h4>
              <div className="p-3 bg-slate-700/30 rounded-lg text-sm text-slate-300">
                {selectedTranscript ? (
                  <span className="italic">&ldquo;{selectedTranscript}&rdquo;</span>
                ) : (
                  <span className="text-slate-500">
                    No messages from this agent through round {selectedRound} yet.
                  </span>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={() => setIsNodeModalOpen(false)}
                className="flex-1"
              >
                Close
              </Button>
              <Link href={`/simulations/${simulationId}/chat?agent=${selectedNode.id}`}>
                <Button className="flex-1">
                  Chat with Agent
                </Button>
              </Link>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
