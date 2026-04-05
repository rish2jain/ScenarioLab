'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, Copy, GitCompare } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { SIMULATION_ENVIRONMENTS, type SimulationEnvironmentId } from '@/lib/environment-types';

/** Minimal runnable preset: at least one agent so POST /api/simulations succeeds. */
const DEFAULT_BASE = `{
  "name": "Comparison base",
  "description": "",
  "playbook_id": null,
  "environment_type": "boardroom",
  "agents": [
    { "name": "Stakeholder A", "archetype_id": "ceo" }
  ],
  "total_rounds": 5,
  "seed_ids": [],
  "parameters": {}
}`;

export default function CompareScenariosPage() {
  const { addToast } = useToast();
  const [nameA, setNameA] = useState('Scenario A');
  const [nameB, setNameB] = useState('Scenario B');
  const [envB, setEnvB] = useState<SimulationEnvironmentId>('war_room');
  const [baseJson, setBaseJson] = useState(DEFAULT_BASE);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdIds, setCreatedIds] = useState<{ a: string; b: string } | null>(null);

  const runPreset = async () => {
    setError('');
    setResult(null);
    let base: Record<string, unknown>;
    try {
      base = JSON.parse(baseJson) as Record<string, unknown>;
    } catch {
      setError('Base config must be valid JSON.');
      return;
    }
    setLoading(true);
    setCreatedIds(null);
    try {
      const out = await api.dualRunPreset({
        name_a: nameA,
        name_b: nameB,
        base,
        environment_type_b: envB,
      });
      if (!out) {
        setError(
          'Could not build preset — check the backend and that JSON matches POST /api/simulations.'
        );
      } else {
        setResult(out);
        setError('');
      }
    } catch (err) {
      console.error('compare dualRunPreset failed', err);
      const detail =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'Unknown error';
      setError(`Unexpected error while calling the API: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const createBothSimulations = async () => {
    let base: Record<string, unknown>;
    try {
      base = JSON.parse(baseJson) as Record<string, unknown>;
    } catch {
      setError('Base config must be valid JSON.');
      return;
    }
    setError('');
    setCreating(true);
    setCreatedIds(null);
    try {
      const pair = await api.dualRunPresetAndCreate({
        name_a: nameA,
        name_b: nameB,
        base,
        environment_type_b: envB,
      });
      const idA = pair?.a && typeof pair.a === 'object' ? pair.a.id : undefined;
      const idB = pair?.b && typeof pair.b === 'object' ? pair.b.id : undefined;
      if (
        typeof idA !== 'string' ||
        !idA ||
        typeof idB !== 'string' ||
        !idB
      ) {
        const msg = 'Create response was missing simulation ids.';
        setError(msg);
        addToast(msg, 'error');
        return;
      }
      setCreatedIds({ a: idA, b: idB });
      addToast('Both simulations created. Open them from the links below.', 'success');
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : typeof err === 'string' ? err : 'Unknown error';
      setError(`Create failed: ${detail}`);
      addToast(detail, 'error');
    } finally {
      setCreating(false);
    }
  };

  const copyResultJson = async (text: string) => {
    if (
      typeof navigator === 'undefined' ||
      !navigator.clipboard ||
      typeof navigator.clipboard.writeText !== 'function'
    ) {
      addToast(
        'Clipboard not supported in this browser or insecure context',
        'error'
      );
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      addToast('Copied to clipboard', 'success');
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : 'permission denied or blocked';
      addToast(`Could not copy to clipboard (${detail})`, 'error');
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl mx-auto px-4 py-6">
      <div className="flex items-center gap-4">
        <Link href="/simulations">
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Simulations
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <GitCompare className="w-7 h-7 text-accent" />
            Compare scenarios
          </h1>
          <p className="text-foreground-muted text-sm mt-1">
            Build two create payloads from one base config. Tag runs with{' '}
            <code className="text-xs bg-background-secondary px-1 rounded">batch_parent_id</code> in parameters when
            you create simulations (optional cross-sim analytics).
          </p>
        </div>
      </div>

      <Card
        header={<span className="font-semibold text-foreground">Dual-run preset</span>}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Scenario A name" value={nameA} onChange={(e) => setNameA(e.target.value)} />
            <Input label="Scenario B name" value={nameB} onChange={(e) => setNameB(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground-muted mb-2">Environment for scenario B</label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              value={envB}
              onChange={(e) => setEnvB(e.target.value as SimulationEnvironmentId)}
            >
              {SIMULATION_ENVIRONMENTS.map((e) => (
                <option key={e.value} value={e.value}>
                  {e.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground-muted mb-2">
              Base simulation create body (JSON)
            </label>
            <textarea
              className="w-full min-h-[200px] font-mono text-xs rounded-lg border border-border bg-background px-3 py-2 text-foreground"
              value={baseJson}
              onChange={(e) => setBaseJson(e.target.value)}
              spellCheck={false}
            />
          </div>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          <Button onClick={() => void runPreset()} isLoading={loading}>
            Generate two configs
          </Button>
        </div>
      </Card>

      {result ? (
        <Card header={<span className="font-semibold text-foreground">Result</span>}>
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <p className="text-sm text-foreground-muted">
                <span className="text-foreground font-medium">batch_parent_id:</span>{' '}
                {String(result.batch_parent_id ?? '')}
              </p>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Copy className="w-4 h-4" />}
                onClick={() => void copyResultJson(JSON.stringify(result, null, 2))}
              >
                Copy JSON
              </Button>
            </div>
            <pre className="text-xs bg-background-secondary/80 p-3 rounded-lg overflow-x-auto text-foreground-muted max-h-96 overflow-y-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => void createBothSimulations()}
                isLoading={creating}
                disabled={creating}
              >
                Create both simulations
              </Button>
            </div>
            {createdIds ? (
              <div className="text-sm space-y-2 rounded-lg border border-border bg-background-secondary/40 p-3">
                <p className="text-foreground font-medium">Created runs</p>
                <div className="flex flex-wrap gap-3">
                  <Link
                    href={`/simulations/${createdIds.a}`}
                    className="text-accent hover:underline"
                  >
                    Open scenario A
                  </Link>
                  <Link
                    href={`/simulations/${createdIds.b}`}
                    className="text-accent hover:underline"
                  >
                    Open scenario B
                  </Link>
                  <Link href="/analytics/cross-simulation" className="text-foreground-muted hover:underline text-sm">
                    Cross-simulation analytics
                  </Link>
                </div>
              </div>
            ) : null}
            <p className="text-xs text-foreground-muted">
              <code className="px-1 rounded bg-background-secondary">batch_parent_id</code> is included in each
              scenario&apos;s <code className="px-1 rounded bg-background-secondary">parameters</code> for
              cross-sim analytics. Creating both runs uses{' '}
              <code className="px-1 rounded bg-background-secondary">POST /api/simulations/dual-run-preset-create</code>{' '}
              (rollback-safe). For custom payloads,{' '}
              <code className="px-1 rounded bg-background-secondary">POST /api/simulations/dual-create</code> with{' '}
              <code className="px-1 rounded bg-background-secondary">scenario_a</code> and{' '}
              <code className="px-1 rounded bg-background-secondary">scenario_b</code>.
            </p>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
