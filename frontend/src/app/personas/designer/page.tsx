'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ChevronLeft,
  User,
  Save,
  AlertTriangle,
  CheckCircle,
  Trash2,
  Plus,
  RefreshCw,
  FilePlus2,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { api } from '@/lib/api';
import type { CustomPersonaConfig, CoherenceWarning } from '@/lib/types';

const STALE_MS = 30 * 24 * 60 * 60 * 1000;

function isResearchStale(iso: string | null | undefined): boolean {
  if (iso == null || iso === '') return true;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return true;
  return Date.now() - t > STALE_MS;
}

function emptyPersona(): CustomPersonaConfig {
  return {
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
  };
}

const riskToleranceOptions = ['conservative', 'moderate', 'aggressive'];
const informationBiasOptions = ['qualitative', 'quantitative', 'balanced'];
const decisionSpeedOptions = ['fast', 'moderate', 'slow'];

export default function PersonaDesignerPage() {
  const [personas, setPersonas] = useState<CustomPersonaConfig[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [currentPersona, setCurrentPersona] = useState<CustomPersonaConfig>(emptyPersona);
  const [warnings, setWarnings] = useState<CoherenceWarning[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [newIncentive, setNewIncentive] = useState('');
  const [newAxiom, setNewAxiom] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeletingPersona, setIsDeletingPersona] = useState(false);

  const loadList = useCallback(async () => {
    setListLoading(true);
    setListError('');
    try {
      const rows = await api.listCustomPersonas();
      setPersonas(rows);
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Failed to load personas');
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    const controller = new AbortController();
    const id = window.setTimeout(() => {
      void (async () => {
        const { signal } = controller;
        if (signal.aborted) return;
        if (!currentPersona.name.trim() && !currentPersona.role.trim()) {
          if (!signal.aborted) setWarnings([]);
          return;
        }
        try {
          const res = await api.validatePersonaCoherence(
            currentPersona as unknown as Record<string, unknown>,
            { signal }
          );
          if (signal.aborted) return;
          setWarnings(api.mapCoherenceWarnings(res.warnings));
        } catch (err) {
          if (signal.aborted) return;
          console.error('validatePersonaCoherence failed', err);
        }
      })();
    }, 450);
    return () => {
      window.clearTimeout(id);
      controller.abort();
    };
  }, [currentPersona]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (currentPersona.id) {
        const { id, ...rest } = currentPersona;
        const updated = await api.updateCustomPersona(
          id,
          rest as unknown as Record<string, unknown>
        );
        if (updated) {
          setPersonas((p) => p.map((x) => (x.id === updated.id ? updated : x)));
          setCurrentPersona(updated);
        }
      } else {
        const rest = Object.fromEntries(
          Object.entries(currentPersona).filter(([key]) => key !== 'id')
        );
        const created = await api.createCustomPersona(rest as unknown as Record<string, unknown>);
        if (created?.id) {
          setPersonas((p) => [...p, created]);
          setCurrentPersona(created);
        }
      }
    } catch {
      setListError('Save failed — check backend and try again.');
    }
    setIsSaving(false);
  };

  const handleLoadPersona = (persona: CustomPersonaConfig) => {
    setCurrentPersona({ ...persona });
  };

  const handleNewPersona = () => {
    setCurrentPersona(emptyPersona());
  };

  const handleDeletePersona = (id: string) => {
    if (!id) return;
    setPendingDeleteId(id);
  };

  const handleCancelDeletePersona = () => {
    if (isDeletingPersona) return;
    setPendingDeleteId(null);
  };

  const handleConfirmDeletePersona = async () => {
    if (pendingDeleteId == null) return;
    const id = pendingDeleteId;
    setIsDeletingPersona(true);
    try {
      const ok = await api.deleteCustomPersona(id);
      if (ok) {
        setPersonas((p) => p.filter((x) => x.id !== id));
        setCurrentPersona((cur) => (cur.id === id ? emptyPersona() : cur));
        setPendingDeleteId(null);
      } else {
        setListError('Delete failed — try again.');
      }
    } catch {
      setListError('Delete failed — try again.');
    } finally {
      setIsDeletingPersona(false);
    }
  };

  const handleRefreshResearch = async () => {
    const pid = currentPersona.id;
    if (!pid) return;
    setRefreshingId(pid);
    try {
      const updated = await api.refreshDesignerPersonaResearch(pid);
      if (updated) {
        setPersonas((p) => p.map((x) => (x.id === updated.id ? updated : x)));
        setCurrentPersona(updated);
      }
    } catch (e) {
      setListError(
        e instanceof Error ? e.message : 'Failed to refresh research — try again.',
      );
    } finally {
      setRefreshingId(null);
    }
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
      incentive_structure: currentPersona.incentive_structure?.filter((i) => i !== incentive) || [],
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
      behavioral_axioms: currentPersona.behavioral_axioms?.filter((a) => a !== axiom) || [],
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Custom Persona Designer</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Create personas backed by the API; refresh web evidence when it goes stale
          </p>
        </div>
      </div>

      {listError ? (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {listError}
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card
            header={
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <User className="w-5 h-5 text-accent" />
                  <h2 className="text-lg font-semibold text-slate-100">Persona Configuration</h2>
                </div>
                <Button variant="secondary" size="sm" leftIcon={<FilePlus2 className="w-4 h-4" />} onClick={handleNewPersona}>
                  New
                </Button>
              </div>
            }
          >
            <div className="space-y-6">
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
                  value={currentPersona.description ?? ''}
                  onChange={(e) => setCurrentPersona({ ...currentPersona, description: e.target.value })}
                  className="w-full h-20 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent resize-none"
                  placeholder="Describe this persona..."
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400">Authority Level</label>
                  <span className="text-sm text-slate-200">{currentPersona.authority_level ?? 5}/10</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={currentPersona.authority_level ?? 5}
                  onChange={(e) =>
                    setCurrentPersona({ ...currentPersona, authority_level: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400">Coalition Tendencies</label>
                  <span className="text-sm text-slate-200">
                    {Math.round((currentPersona.coalition_tendencies || 0) * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={(currentPersona.coalition_tendencies || 0) * 100}
                  onChange={(e) =>
                    setCurrentPersona({
                      ...currentPersona,
                      coalition_tendencies: parseInt(e.target.value, 10) / 100,
                    })
                  }
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Select
                  label="Risk Tolerance"
                  value={currentPersona.risk_tolerance || 'moderate'}
                  onChange={(val) =>
                    setCurrentPersona({
                      ...currentPersona,
                      risk_tolerance: val as CustomPersonaConfig['risk_tolerance'],
                    })
                  }
                  options={riskToleranceOptions.map((opt) => ({
                    value: opt,
                    label: opt.charAt(0).toUpperCase() + opt.slice(1),
                  }))}
                />
                <Select
                  label="Information Bias"
                  value={currentPersona.information_bias || 'balanced'}
                  onChange={(val) =>
                    setCurrentPersona({
                      ...currentPersona,
                      information_bias: val as CustomPersonaConfig['information_bias'],
                    })
                  }
                  options={informationBiasOptions.map((opt) => ({
                    value: opt,
                    label: opt.charAt(0).toUpperCase() + opt.slice(1),
                  }))}
                />
                <Select
                  label="Decision Speed"
                  value={currentPersona.decision_speed || 'moderate'}
                  onChange={(val) =>
                    setCurrentPersona({
                      ...currentPersona,
                      decision_speed: val as CustomPersonaConfig['decision_speed'],
                    })
                  }
                  options={decisionSpeedOptions.map((opt) => ({
                    value: opt,
                    label: opt.charAt(0).toUpperCase() + opt.slice(1),
                  }))}
                />
              </div>

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
                        type="button"
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
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addIncentive();
                      }
                    }}
                    className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="Add incentive..."
                  />
                  <Button type="button" size="sm" onClick={addIncentive}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              </div>

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
                        type="button"
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
                    onKeyDown={(e) => {
                      if (e.key !== 'Enter') return;
                      if (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
                      if (e.nativeEvent?.isComposing) return;
                      e.preventDefault();
                      addAxiom();
                    }}
                    className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="Add axiom..."
                  />
                  <Button type="button" size="sm" onClick={addAxiom}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {currentPersona.evidence_summary ? (
                <div className="p-3 rounded-lg bg-slate-700/30 border border-slate-600 text-sm text-slate-300 max-h-40 overflow-y-auto">
                  <div className="text-slate-400 text-xs mb-1">Evidence summary</div>
                  {currentPersona.evidence_summary}
                </div>
              ) : null}

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

              <div className="flex flex-col sm:flex-row gap-2">
                <Button
                  className="flex-1"
                  leftIcon={<Save className="w-4 h-4" />}
                  onClick={() => void handleSave()}
                  isLoading={isSaving}
                  disabled={!currentPersona.name || !currentPersona.role}
                >
                  {currentPersona.id ? 'Update persona' : 'Save persona'}
                </Button>
                {currentPersona.id ? (
                  <Button
                    variant="secondary"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                    onClick={() => void handleRefreshResearch()}
                    isLoading={refreshingId === currentPersona.id}
                  >
                    Refresh research
                  </Button>
                ) : null}
              </div>
            </div>
          </Card>
        </div>

        <div>
          <Card
            header={
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Saved Personas</h2>
              </div>
            }
          >
            {listLoading ? (
              <Spinner size="sm" className="py-8" message="Loading personas…" />
            ) : (
              <div className="space-y-3">
                {personas.map((persona) => (
                  <div
                    key={persona.id}
                    className="p-4 bg-slate-700/20 rounded-lg hover:bg-slate-700/30 transition-colors cursor-pointer"
                    onClick={() => handleLoadPersona(persona)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-medium text-slate-200">{persona.name}</div>
                        <div className="text-sm text-slate-500">{persona.role}</div>
                        {isResearchStale(persona.last_researched_at) ? (
                          <span className="mt-1 inline-block text-xs px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200">
                            Research stale (&gt;30d or missing)
                          </span>
                        ) : (
                          <span className="mt-1 inline-block text-xs px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-200">
                            Research recent
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (persona.id) handleDeletePersona(persona.id);
                        }}
                        className="p-1 text-slate-500 hover:text-red-400 transition-colors shrink-0"
                        aria-label="Delete persona"
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
                  <div className="text-center py-8 text-slate-500">No custom personas yet — save one on the left</div>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>

      <Modal
        isOpen={pendingDeleteId !== null}
        onClose={handleCancelDeletePersona}
        title="Delete persona?"
        description="Are you sure you want to delete this persona?"
        size="sm"
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={handleCancelDeletePersona}
              disabled={isDeletingPersona}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={() => void handleConfirmDeletePersona()}
              isLoading={isDeletingPersona}
              disabled={isDeletingPersona}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-400">This action cannot be undone.</p>
      </Modal>
    </div>
  );
}
