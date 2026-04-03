'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { ChevronLeft, User, Save, Upload, Download, AlertTriangle, CheckCircle, Trash2, Plus } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type { CustomPersonaConfig, CoherenceWarning } from '@/lib/types';

// Mock saved personas
const mockSavedPersonas: CustomPersonaConfig[] = [
  {
    id: 'persona-1',
    name: 'Aggressive Negotiator',
    role: 'Chief Strategy Officer',
    description: 'Highly competitive and results-driven executive',
    authority_level: 9,
    risk_tolerance: 'aggressive',
    information_bias: 'quantitative',
    decision_speed: 'fast',
    coalition_tendencies: 0.3,
    incentive_structure: ['financial_performance', 'market_share'],
    behavioral_axioms: ['Win at all costs', 'Data drives decisions'],
  },
  {
    id: 'persona-2',
    name: 'Cautious Analyst',
    role: 'Chief Risk Officer',
    description: 'Risk-averse and detail-oriented',
    authority_level: 7,
    risk_tolerance: 'conservative',
    information_bias: 'qualitative',
    decision_speed: 'slow',
    coalition_tendencies: 0.7,
    incentive_structure: ['risk_mitigation', 'compliance'],
    behavioral_axioms: ['Safety first', 'Thorough analysis required'],
  },
];

// Mock coherence warnings
const mockWarnings: CoherenceWarning[] = [
  {
    attribute: 'risk_tolerance + decision_speed',
    message: 'Aggressive risk tolerance with slow decision speed may be inconsistent',
    severity: 'warning',
  },
];

const riskToleranceOptions = ['conservative', 'moderate', 'aggressive'];
const informationBiasOptions = ['qualitative', 'quantitative', 'balanced'];
const decisionSpeedOptions = ['fast', 'moderate', 'slow'];

export default function PersonaDesignerPage() {
  const [personas, setPersonas] = useState<CustomPersonaConfig[]>([]);
  const [currentPersona, setCurrentPersona] = useState<CustomPersonaConfig>({
    name: '',
    role: '',
    description: '',
    authority_level: 5,
    risk_tolerance: 'moderate',
    information_bias: 'balanced',
    decision_speed: 'moderate',
    coalition_tendencies: 0.5,
    incentive_structure: [],
    behavioral_axioms: [],
  });
  const [warnings, setWarnings] = useState<CoherenceWarning[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [newIncentive, setNewIncentive] = useState('');
  const [newAxiom, setNewAxiom] = useState('');

  useEffect(() => {
    // Load saved personas
    setPersonas(mockSavedPersonas);
  }, []);

  // Validate coherence when persona changes
  useEffect(() => {
    const validateCoherence = async () => {
      try {
        // Mock validation
        if (currentPersona.risk_tolerance === 'aggressive' && currentPersona.decision_speed === 'slow') {
          setWarnings(mockWarnings);
        } else {
          setWarnings([]);
        }
      } catch {
        setWarnings([]);
      }
    };

    validateCoherence();
  }, [currentPersona]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const newPersona: CustomPersonaConfig = {
        ...currentPersona,
        id: `persona-${Date.now()}`,
      };
      setPersonas([...personas, newPersona]);
      // Reset form
      setCurrentPersona({
        name: '',
        role: '',
        description: '',
        authority_level: 5,
        risk_tolerance: 'moderate',
        information_bias: 'balanced',
        decision_speed: 'moderate',
        coalition_tendencies: 0.5,
        incentive_structure: [],
        behavioral_axioms: [],
      });
    } catch {
      // Handle error
    }
    setIsSaving(false);
  };

  const handleLoadPersona = (persona: CustomPersonaConfig) => {
    setCurrentPersona(persona);
  };

  const handleDeletePersona = (id: string) => {
    setPersonas(personas.filter(p => p.id !== id));
  };

  const addIncentive = () => {
    if (newIncentive && !currentPersona.incentive_structure?.includes(newIncentive)) {
      setCurrentPersona({
        ...currentPersona,
        incentive_structure: [...(currentPersona.incentive_structure || []), newIncentive],
      });
      setNewIncentive('');
    }
  };

  const removeIncentive = (incentive: string) => {
    setCurrentPersona({
      ...currentPersona,
      incentive_structure: currentPersona.incentive_structure?.filter(i => i !== incentive) || [],
    });
  };

  const addAxiom = () => {
    if (newAxiom && !currentPersona.behavioral_axioms?.includes(newAxiom)) {
      setCurrentPersona({
        ...currentPersona,
        behavioral_axioms: [...(currentPersona.behavioral_axioms || []), newAxiom],
      });
      setNewAxiom('');
    }
  };

  const removeAxiom = (axiom: string) => {
    setCurrentPersona({
      ...currentPersona,
      behavioral_axioms: currentPersona.behavioral_axioms?.filter(a => a !== axiom) || [],
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/personas">
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Custom Persona Designer</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Create and customize agent personas
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Designer Form */}
        <div className="lg:col-span-2 space-y-6">
          <Card
            header={
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Persona Configuration</h2>
              </div>
            }
          >
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Name</label>
                  <input
                    type="text"
                    value={currentPersona.name}
                    onChange={(e) => setCurrentPersona({ ...currentPersona, name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="e.g., Aggressive Negotiator"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Role</label>
                  <input
                    type="text"
                    value={currentPersona.role}
                    onChange={(e) => setCurrentPersona({ ...currentPersona, role: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="e.g., Chief Strategy Officer"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Description</label>
                <textarea
                  value={currentPersona.description}
                  onChange={(e) => setCurrentPersona({ ...currentPersona, description: e.target.value })}
                  className="w-full h-20 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent resize-none"
                  placeholder="Describe this persona..."
                />
              </div>

              {/* Authority Level Slider */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400">Authority Level</label>
                  <span className="text-sm text-slate-200">{currentPersona.authority_level}/10</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={currentPersona.authority_level}
                  onChange={(e) => setCurrentPersona({ ...currentPersona, authority_level: parseInt(e.target.value) })}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              {/* Coalition Tendencies Slider */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400">Coalition Tendencies</label>
                  <span className="text-sm text-slate-200">{Math.round((currentPersona.coalition_tendencies || 0) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={(currentPersona.coalition_tendencies || 0) * 100}
                  onChange={(e) => setCurrentPersona({ ...currentPersona, coalition_tendencies: parseInt(e.target.value) / 100 })}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              {/* Select Options */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Risk Tolerance</label>
                  <select
                    value={currentPersona.risk_tolerance}
                    onChange={(e) => setCurrentPersona({ ...currentPersona, risk_tolerance: e.target.value as typeof currentPersona.risk_tolerance })}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  >
                    {riskToleranceOptions.map(opt => (
                      <option key={opt} value={opt}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Information Bias</label>
                  <select
                    value={currentPersona.information_bias}
                    onChange={(e) => setCurrentPersona({ ...currentPersona, information_bias: e.target.value as typeof currentPersona.information_bias })}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  >
                    {informationBiasOptions.map(opt => (
                      <option key={opt} value={opt}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Decision Speed</label>
                  <select
                    value={currentPersona.decision_speed}
                    onChange={(e) => setCurrentPersona({ ...currentPersona, decision_speed: e.target.value as typeof currentPersona.decision_speed })}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  >
                    {decisionSpeedOptions.map(opt => (
                      <option key={opt} value={opt}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Incentive Structure */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Incentive Structure</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {currentPersona.incentive_structure?.map((incentive) => (
                    <span
                      key={incentive}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-slate-600/30 rounded text-sm text-slate-300"
                    >
                      {incentive}
                      <button
                        onClick={() => removeIncentive(incentive)}
                        className="text-slate-500 hover:text-red-400"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newIncentive}
                    onChange={(e) => setNewIncentive(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addIncentive()}
                    className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="Add incentive..."
                  />
                  <Button size="sm" onClick={addIncentive}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* Behavioral Axioms */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Behavioral Axioms</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {currentPersona.behavioral_axioms?.map((axiom) => (
                    <span
                      key={axiom}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-slate-600/30 rounded text-sm text-slate-300"
                    >
                      {axiom}
                      <button
                        onClick={() => removeAxiom(axiom)}
                        className="text-slate-500 hover:text-red-400"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newAxiom}
                    onChange={(e) => setNewAxiom(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addAxiom()}
                    className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="Add axiom..."
                  />
                  <Button size="sm" onClick={addAxiom}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* Coherence Warnings */}
              {warnings.length > 0 && (
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                    <span className="font-medium text-yellow-400">Coherence Warnings</span>
                  </div>
                  <ul className="space-y-1">
                    {warnings.map((warning, idx) => (
                      <li key={idx} className="text-sm text-yellow-400/80 flex items-start gap-2">
                        <span>•</span>
                        {warning.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Save Button */}
              <Button
                className="w-full"
                leftIcon={<Save className="w-4 h-4" />}
                onClick={handleSave}
                isLoading={isSaving}
                disabled={!currentPersona.name || !currentPersona.role}
              >
                Save Persona
              </Button>
            </div>
          </Card>
        </div>

        {/* Saved Personas */}
        <div>
          <Card
            header={
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Saved Personas</h2>
              </div>
            }
          >
            <div className="space-y-3">
              {personas.map((persona) => (
                <div
                  key={persona.id}
                  className="p-4 bg-slate-700/20 rounded-lg hover:bg-slate-700/30 transition-colors cursor-pointer"
                  onClick={() => handleLoadPersona(persona)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-slate-200">{persona.name}</div>
                      <div className="text-sm text-slate-500">{persona.role}</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePersona(persona.id || '');
                      }}
                      className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    <span className="px-1.5 py-0.5 bg-slate-600/30 rounded text-xs text-slate-400 capitalize">
                      {persona.risk_tolerance}
                    </span>
                    <span className="px-1.5 py-0.5 bg-slate-600/30 rounded text-xs text-slate-400 capitalize">
                      {persona.decision_speed}
                    </span>
                  </div>
                </div>
              ))}
              {personas.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  No custom personas saved yet
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
