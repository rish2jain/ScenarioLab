'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Users, Share2, Filter } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { NetworkGraph } from '@/components/visualization/NetworkGraph';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { Simulation, NetworkNode, NetworkEdge, NetworkGraphData, AgentArchetype } from '@/lib/types';

// Mock data generator for network graph
function generateMockNetworkData(round: number): NetworkGraphData {
  const roles = [
    'Acquiring CEO', 'Target CEO', 'Integration Lead', 'HR Director', 
    'Employee Rep', 'Board Member', 'Union Leader', 'CFO',
    'Legal Counsel', 'Communications Lead', 'Operations VP', 'IT Director'
  ];
  
  const archetypes: AgentArchetype[] = ['aggressor', 'defender', 'mediator', 'analyst', 'influencer', 'skeptic'];
  
  const colors = [
    '#14b8a6', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', 
    '#22c55e', '#ec4899', '#06b6d4', '#f97316', '#84cc16'
  ];

  const coalitions = ['Pro-Merger', 'Anti-Merger', 'Neutral', 'Undecided'];

  // Generate 25 nodes
  const nodes: NetworkNode[] = Array.from({ length: 25 }, (_, i) => ({
    id: `agent-${i + 1}`,
    name: `Agent ${i + 1}`,
    role: roles[i % roles.length],
    archetype: archetypes[i % archetypes.length],
    color: colors[i % colors.length],
    authorityLevel: Math.floor(Math.random() * 8) + 2, // 2-10
    coalition: coalitions[i % coalitions.length],
  }));

  // Generate ~60 edges with varying sentiment
  const edges: NetworkEdge[] = [];
  const edgeSet = new Set<string>();
  
  for (let i = 0; i < 60; i++) {
    const sourceIdx = Math.floor(Math.random() * nodes.length);
    let targetIdx = Math.floor(Math.random() * nodes.length);
    while (targetIdx === sourceIdx) {
      targetIdx = Math.floor(Math.random() * nodes.length);
    }
    
    const edgeKey = [sourceIdx, targetIdx].sort().join('-');
    if (edgeSet.has(edgeKey)) continue;
    edgeSet.add(edgeKey);

    const sentimentScore = (Math.random() - 0.5) * 2; // -1 to 1
    let sentiment: NetworkEdge['sentiment'] = 'neutral';
    if (sentimentScore > 0.3) sentiment = 'positive';
    else if (sentimentScore < -0.3) sentiment = 'negative';

    edges.push({
      id: `edge-${i}`,
      source: nodes[sourceIdx].id,
      target: nodes[targetIdx].id,
      sentiment,
      sentimentScore,
      messageCount: Math.floor(Math.random() * 20) + 1,
    });
  }

  return { nodes, edges, round };
}

export default function NetworkGraphPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentSimulation, setCurrentSimulation } = useSimulationStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRound, setSelectedRound] = useState(1);
  const [networkData, setNetworkData] = useState<NetworkGraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [isNodeModalOpen, setIsNodeModalOpen] = useState(false);
  
  // Filter states
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedCoalitions, setSelectedCoalitions] = useState<string[]>([]);
  const [sentimentThreshold, setSentimentThreshold] = useState(-1);

  useEffect(() => {
    const loadSimulation = async () => {
      setIsLoading(true);
      const simulationData = await api.getSimulation(simulationId);
      
      if (simulationData) {
        setCurrentSimulation(simulationData);
        setSelectedRound(simulationData.currentRound || 1);
        setNetworkData(generateMockNetworkData(simulationData.currentRound || 1));
      }
      setIsLoading(false);
    };

    loadSimulation();
  }, [simulationId, setCurrentSimulation]);

  // Update network data when round changes
  useEffect(() => {
    if (currentSimulation) {
      setNetworkData(generateMockNetworkData(selectedRound));
    }
  }, [selectedRound, currentSimulation]);

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading network visualization...</div>
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
        <div className="flex-1 bg-slate-900/50 overflow-auto">
          <div className="min-w-[600px] h-full">
            <NetworkGraph
              data={networkData}
              width={1200}
              height={800}
              onNodeClick={handleNodeClick}
              selectedNodeId={selectedNode?.id}
              filterRoles={selectedRoles}
              filterCoalitions={selectedCoalitions}
              sentimentThreshold={sentimentThreshold}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-slate-700 bg-slate-800/30 overflow-y-auto max-h-64 lg:max-h-none flex-shrink-0">
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

            {/* Coalition Filter */}
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
              <div className="p-3 bg-slate-700/30 rounded-lg text-sm text-slate-300 italic">
                &ldquo;I believe we need to carefully consider the implications of this approach 
                before moving forward with any definitive action...&rdquo;
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
