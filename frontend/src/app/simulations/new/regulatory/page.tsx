'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Gavel, Sparkles, FileText, Building2, AlertTriangle, Play } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { SeverityLevel } from '@/lib/types';

interface GeneratedScenario {
  name: string;
  description: string;
  environment_type: string;
  agents: Array<{
    role: string;
    archetype: string;
    description: string;
  }>;
  rounds: number;
  key_issues: string[];
  impact_assessment: {
    compliance_risk: SeverityLevel;
    operational_impact: SeverityLevel;
    timeline_pressure: SeverityLevel;
    financial_exposure: SeverityLevel;
  };
  suggested_objectives: string[];
}

const industries = [
  'Technology',
  'Financial Services',
  'Healthcare',
  'Energy',
  'Manufacturing',
  'Retail',
  'Telecommunications',
  'Transportation',
];

const riskColors: Record<string, string> = {
  low: 'bg-green-500/20 text-green-400',
  medium: 'bg-yellow-500/20 text-yellow-400',
  high: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
};

export default function RegulatoryGeneratorPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const [regulatoryText, setRegulatoryText] = useState('');
  const [industry, setIndustry] = useState('');
  const [organizationContext, setOrganizationContext] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedScenario, setGeneratedScenario] = useState<GeneratedScenario | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setLoadError(null);
    try {
      const scenario = await api.generateRegulatoryScenario({
        regulatory_text: regulatoryText,
        industry: industry.toLowerCase().replace(/\s+/g, '_'),
        organization_context: organizationContext,
      });
      setGeneratedScenario(scenario);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Could not generate regulatory scenario.';
      setGeneratedScenario(null);
      setLoadError(message);
      addToast(message, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateSimulation = () => {
    // Navigate to simulation creation with generated config
    router.push('/simulations/new');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/simulations/new">
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Regulatory Scenario Generator</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Generate war-gaming scenarios from regulatory text
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="space-y-6">
          <Card
            header={
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Regulatory Input</h2>
              </div>
            }
          >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Regulatory Text
                </label>
                <textarea
                  value={regulatoryText}
                  onChange={(e) => setRegulatoryText(e.target.value)}
                  className="w-full h-48 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent resize-none"
                  placeholder="Paste regulatory text here (e.g., GDPR Article 17, SEC Rule 10b-5, etc.)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Industry
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                >
                  <option value="">Select industry...</option>
                  {industries.map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Organization Context (Optional)
                </label>
                <textarea
                  value={organizationContext}
                  onChange={(e) => setOrganizationContext(e.target.value)}
                  className="w-full h-24 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent resize-none"
                  placeholder="Describe your organization size, structure, or specific context..."
                />
              </div>

              <Button
                className="w-full"
                leftIcon={<Sparkles className="w-4 h-4" />}
                onClick={handleGenerate}
                isLoading={isGenerating}
                disabled={!regulatoryText || !industry}
              >
                Generate Scenario
              </Button>
            </div>
          </Card>
        </div>

        {/* Output Section */}
        <div className="space-y-6">
          {loadError && (
            <Card>
              <div className="text-sm text-red-400">{loadError}</div>
            </Card>
          )}
          {generatedScenario ? (
            <>
              <Card
                header={
                  <div className="flex items-center gap-2">
                    <Gavel className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold text-slate-100">Generated Scenario</h2>
                  </div>
                }
              >
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xl font-bold text-slate-100">{generatedScenario.name}</h3>
                    <p className="text-slate-400 mt-1">{generatedScenario.description}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-slate-500" />
                    <span className="text-sm text-slate-400">Environment: </span>
                    <span className="text-sm text-slate-200 capitalize">{generatedScenario.environment_type}</span>
                    <span className="text-slate-500 mx-2">•</span>
                    <span className="text-sm text-slate-400">{generatedScenario.rounds} rounds</span>
                  </div>
                </div>
              </Card>

              {/* Impact Assessment */}
              <Card
                header={
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold text-slate-100">Impact Assessment</h2>
                  </div>
                }
              >
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(generatedScenario.impact_assessment).map(([key, value]) => (
                    <div key={key} className="p-3 bg-slate-700/20 rounded-lg">
                      <div className="text-sm text-slate-400 capitalize mb-1">
                        {key.replaceAll('_', ' ')}
                      </div>
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${riskColors[value]}`}>
                        {value.charAt(0).toUpperCase() + value.slice(1)}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Key Issues */}
              <Card
                header={
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold text-slate-100">Key Issues</h2>
                  </div>
                }
              >
                <ul className="space-y-2">
                  {generatedScenario.key_issues.map((issue, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-accent mt-1">•</span>
                      <span className="text-slate-300">{issue}</span>
                    </li>
                  ))}
                </ul>
              </Card>

              {/* Suggested Agents */}
              <Card
                header={
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold text-slate-100">Suggested Agents</h2>
                  </div>
                }
              >
                <div className="space-y-2">
                  {generatedScenario.agents.map((agent, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-slate-700/20 rounded-lg">
                      <div>
                        <span className="font-medium text-slate-200">{agent.role}</span>
                        <p className="text-sm text-slate-500">{agent.description}</p>
                      </div>
                      <span className="px-2 py-1 bg-slate-600/30 rounded text-xs text-slate-400 capitalize">
                        {agent.archetype}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Suggested Objectives */}
              <Card
                header={
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold text-slate-100">Suggested Objectives</h2>
                  </div>
                }
              >
                <ul className="space-y-2">
                  {generatedScenario.suggested_objectives.map((objective, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-accent mt-1">{index + 1}.</span>
                      <span className="text-slate-300">{objective}</span>
                    </li>
                  ))}
                </ul>
              </Card>

              {/* Create Simulation Button */}
              <Button
                className="w-full"
                size="lg"
                leftIcon={<Play className="w-5 h-5" />}
                onClick={handleCreateSimulation}
              >
                Create Simulation with This Scenario
              </Button>
            </>
          ) : !loadError ? (
            <Card className="h-full flex items-center justify-center min-h-[400px]">
              <div className="text-center text-slate-500">
                <Gavel className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Generate a scenario to see results</p>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
