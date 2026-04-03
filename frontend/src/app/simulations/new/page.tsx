'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Building2,
  ShieldAlert,
  Swords,
  Users,
  ChevronLeft,
  ChevronRight,
  Check,
  Plus,
  Minus,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StepWizard } from '@/components/ui/StepWizard';
import { Slider } from '@/components/ui/Slider';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { usePlaybookStore, useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { Playbook, Agent } from '@/lib/types';

const steps = [
  { id: 'playbook', label: 'Select Playbook' },
  { id: 'agents', label: 'Configure Agents' },
  { id: 'parameters', label: 'Set Parameters' },
  { id: 'review', label: 'Review & Launch' },
];

const iconMap: Record<string, React.ReactNode> = {
  Building2: <Building2 className="w-8 h-8" />,
  ShieldAlert: <ShieldAlert className="w-8 h-8" />,
  Swords: <Swords className="w-8 h-8" />,
  Users: <Users className="w-8 h-8" />,
};

export default function NewSimulationPage() {
  const router = useRouter();
  const { playbooks, setPlaybooks, selectedPlaybook, setSelectedPlaybook } = usePlaybookStore();
  const addSimulation = useSimulationStore((state) => state.addSimulation);
  
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [simulationName, setSimulationName] = useState('');
  const [rounds, setRounds] = useState(10);
  const [environmentType, setEnvironmentType] = useState('standard');
  const [modelSelection, setModelSelection] = useState('gpt-4');
  const [monteCarloIterations, setMonteCarloIterations] = useState(100);
  const [agentConfigs, setAgentConfigs] = useState<Record<string, number>>({});

  useEffect(() => {
    const loadPlaybooks = async () => {
      const data = await api.getPlaybooks();
      setPlaybooks(data);
    };
    loadPlaybooks();
  }, [setPlaybooks]);

  useEffect(() => {
    if (selectedPlaybook) {
      const configs: Record<string, number> = {};
      selectedPlaybook.roster.forEach((role) => {
        configs[role.role] = role.defaultCount;
      });
      setAgentConfigs(configs);
      if (!simulationName) {
        setSimulationName(`${selectedPlaybook.name} - ${new Date().toLocaleDateString()}`);
      }
    }
  }, [selectedPlaybook]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleLaunch = async () => {
    if (!selectedPlaybook) return;

    setIsLoading(true);
    
    try {
      const newSimulation = await api.createSimulation({
        name: simulationName,
        playbookId: selectedPlaybook.id,
        playbookName: selectedPlaybook.name,
        status: 'pending',
        config: {
          rounds,
          environmentType,
          modelSelection,
          monteCarloIterations,
        },
        currentRound: 0,
        totalRounds: rounds,
        agents: [],
      });

      addSimulation(newSimulation);
      router.push(`/simulations/${newSimulation.id}`);
    } catch (error) {
      console.error('Failed to create simulation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateAgentCount = (role: string, delta: number) => {
    setAgentConfigs((prev) => ({
      ...prev,
      [role]: Math.max(0, (prev[role] || 0) + delta),
    }));
  };

  const totalAgents = Object.values(agentConfigs).reduce((a, b) => a + b, 0);
  const estimatedCost = totalAgents * rounds * 0.02; // Mock cost calculation

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return !!selectedPlaybook;
      case 1:
        return totalAgents > 0;
      case 2:
        return simulationName.trim().length > 0;
      default:
        return true;
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">New Simulation</h1>
        <p className="text-slate-400 mt-1 text-sm sm:text-base">
          Configure your war-gaming scenario step by step
        </p>
      </div>

      {/* Step Wizard */}
      <Card padding="lg">
        <StepWizard steps={steps} currentStep={currentStep} />
      </Card>

      {/* Step Content */}
      <Card padding="lg">
        {currentStep === 0 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-slate-100">
              Select a Playbook
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {playbooks.map((playbook) => (
                <button
                  key={playbook.id}
                  onClick={() => setSelectedPlaybook(playbook)}
                  className={`p-6 rounded-lg border-2 text-left transition-all ${
                    selectedPlaybook?.id === playbook.id
                      ? 'border-accent bg-accent/10'
                      : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                        selectedPlaybook?.id === playbook.id
                          ? 'bg-accent/20 text-accent'
                          : 'bg-slate-700 text-slate-400'
                      }`}
                    >
                      {iconMap[playbook.icon] || <Building2 className="w-8 h-8" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-100">
                          {playbook.name}
                        </h3>
                        <Badge size="sm">{playbook.category}</Badge>
                      </div>
                      <p className="text-sm text-slate-400 mt-1">
                        {playbook.description}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                        <span>{playbook.typicalDuration}</span>
                        <span>•</span>
                        <span>{playbook.agentCount} agents</span>
                        <span>•</span>
                        <span>{playbook.rounds} rounds</span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === 1 && selectedPlaybook && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                Configure Agents
              </h2>
              <p className="text-slate-400 mt-1">
                Adjust the number of agents for each role in your simulation
              </p>
            </div>
            <div className="space-y-4">
              {selectedPlaybook.roster.map((role) => (
                <div
                  key={role.role}
                  className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-slate-200">{role.role}</h4>
                      {role.required && (
                        <Badge variant="info" size="sm">Required</Badge>
                      )}
                    </div>
                    <p className="text-sm text-slate-400 mt-1">
                      {role.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="default" size="sm">
                        {role.archetype}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => updateAgentCount(role.role, -1)}
                      disabled={agentConfigs[role.role] <= 0}
                      className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-8 text-center font-medium text-slate-100">
                      {agentConfigs[role.role] || 0}
                    </span>
                    <button
                      onClick={() => updateAgentCount(role.role, 1)}
                      className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center text-slate-300 hover:bg-slate-600"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Total Agents</span>
                <span className="text-xl font-semibold text-slate-100">
                  {totalAgents}
                </span>
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                Set Parameters
              </h2>
              <p className="text-slate-400 mt-1">
                Configure the simulation behavior and model settings
              </p>
            </div>
            <div className="space-y-6">
              <Input
                label="Simulation Name"
                value={simulationName}
                onChange={(e) => setSimulationName(e.target.value)}
                placeholder="Enter a name for your simulation"
              />

              <Slider
                label="Number of Rounds"
                min={5}
                max={50}
                value={rounds}
                onChange={setRounds}
              />

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Environment Type
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {['standard', 'stress', 'crisis', 'collaborative'].map((type) => (
                    <button
                      key={type}
                      onClick={() => setEnvironmentType(type)}
                      className={`p-3 rounded-lg border text-sm font-medium capitalize transition-all ${
                        environmentType === type
                          ? 'border-accent bg-accent/10 text-accent'
                          : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Model Selection
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {[
                    { id: 'gpt-4', name: 'GPT-4', desc: 'Best quality' },
                    { id: 'claude-3', name: 'Claude 3', desc: 'Balanced' },
                    { id: 'gpt-3.5', name: 'GPT-3.5', desc: 'Fast & cheap' },
                  ].map((model) => (
                    <button
                      key={model.id}
                      onClick={() => setModelSelection(model.id)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        modelSelection === model.id
                          ? 'border-accent bg-accent/10'
                          : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                      }`}
                    >
                      <div className="font-medium text-slate-200">{model.name}</div>
                      <div className="text-xs text-slate-400">{model.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 p-4 bg-amber-500/10 rounded-lg border border-amber-500/20">
                <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <p className="text-sm text-amber-200">
                  Monte Carlo analysis is available for simulations with 10+ rounds
                </p>
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && selectedPlaybook && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                Review & Launch
              </h2>
              <p className="text-slate-400 mt-1">
                Review your simulation configuration before launching
              </p>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">
                  Configuration Summary
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-400">Name</p>
                    <p className="text-slate-200">{simulationName}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Playbook</p>
                    <p className="text-slate-200">{selectedPlaybook.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Rounds</p>
                    <p className="text-slate-200">{rounds}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Environment</p>
                    <p className="text-slate-200 capitalize">{environmentType}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Model</p>
                    <p className="text-slate-200">{modelSelection}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Total Agents</p>
                    <p className="text-slate-200">{totalAgents}</p>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">
                  Agent Roster
                </h4>
                <div className="space-y-2">
                  {Object.entries(agentConfigs)
                    .filter(([_, count]) => count > 0)
                    .map(([role, count]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className="text-slate-300">{role}</span>
                        <span className="text-slate-200 font-medium">x{count}</span>
                      </div>
                    ))}
                </div>
              </div>

              <div className="p-4 bg-accent/10 rounded-lg border border-accent/30">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-400">Estimated Cost</p>
                    <p className="text-2xl font-bold text-accent">
                      ${estimatedCost.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-slate-400">Estimated Duration</p>
                    <p className="text-slate-200">{selectedPlaybook.typicalDuration}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Navigation */}
      <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={currentStep === 0}
          leftIcon={<ChevronLeft className="w-4 h-4" />}
          className="w-full sm:w-auto"
        >
          Back
        </Button>
        {currentStep < steps.length - 1 ? (
          <Button
            onClick={handleNext}
            disabled={!canProceed()}
            rightIcon={<ChevronRight className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            Next
          </Button>
        ) : (
          <Button
            onClick={handleLaunch}
            disabled={!canProceed() || isLoading}
            isLoading={isLoading}
            leftIcon={!isLoading ? <Check className="w-4 h-4" /> : undefined}
            className="w-full sm:w-auto"
          >
            Launch Simulation
          </Button>
        )}
      </div>
    </div>
  );
}
