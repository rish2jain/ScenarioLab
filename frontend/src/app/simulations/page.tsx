'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, Search, Filter, Clock, Trash2, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from '@/components/ui/Table';
import { useSimulationStore } from '@/lib/store';
import { loadSimulationsFromApi, simulationApi } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

/** Max parallel DELETE calls during bulk delete to avoid overwhelming the API. */
const BULK_DELETE_CONCURRENCY = 5;

/** Max individual error toasts for bulk-delete failures; remainder summarized in one toast. */
const MAX_TOASTS = 5;

export default function SimulationsPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const {
    simulations,
    setSimulations,
    removeSimulation,
    isLoading,
    setLoading,
    setError,
    error: loadError,
  } = useSimulationStore();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) =>
      prev.size === simulations.length
        ? new Set()
        : new Set(simulations.map((s) => s.id))
    );
  }, [simulations]);

  const handleBulkDelete = useCallback(async () => {
    const ids = Array.from(selectedIds);
    const count = ids.length;
    if (count === 0) return;
    if (!window.confirm(`Delete ${count} simulation${count > 1 ? 's' : ''}? This cannot be undone.`)) return;
    setBulkDeleting(true);
    try {
      let deleted = 0;
      const successfulIds: string[] = [];
      const failures: { id: string; message: string }[] = [];
      for (let offset = 0; offset < ids.length; offset += BULK_DELETE_CONCURRENCY) {
        const batch = ids.slice(offset, offset + BULK_DELETE_CONCURRENCY);
        const results = await Promise.allSettled(
          batch.map((id) =>
            simulationApi.deleteSimulation(id).then(() => id)
          )
        );
        results.forEach((result, index) => {
          const id = batch[index];
          if (result.status === 'fulfilled') {
            removeSimulation(id);
            deleted++;
            successfulIds.push(id);
          } else {
            const reason = result.reason;
            const message =
              reason instanceof Error ? reason.message : String(reason);
            failures.push({ id, message });
          }
        });
      }
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const id of successfulIds) {
          next.delete(id);
        }
        return next;
      });
      if (deleted > 0) {
        addToast(`Deleted ${deleted} simulation${deleted > 1 ? 's' : ''}`, 'success');
      }
      failures.slice(0, MAX_TOASTS).forEach(({ id, message }) => {
        addToast(`Failed to delete simulation ${id}: ${message}`, 'error');
      });
      const remaining = failures.length - MAX_TOASTS;
      if (remaining > 0) {
        addToast(`${remaining} more deletions failed`, 'error');
      }
    } finally {
      setBulkDeleting(false);
    }
  }, [selectedIds, removeSimulation, addToast]);

  const handleDelete = useCallback(
    async (id: string, name: string) => {
      if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
      setDeletingId(id);
      try {
        await simulationApi.deleteSimulation(id);
        removeSimulation(id);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        addToast(`Deleted "${name}"`, 'success');
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Delete failed';
        addToast(msg, 'error');
      } finally {
        setDeletingId(null);
      }
    },
    [removeSimulation, addToast]
  );

  useEffect(() => {
    const loadSimulations = async () => {
      setLoading(true);
      try {
        const r = await loadSimulationsFromApi();
        if (!r.ok) {
          addToast('Could not load simulations. Check that the API is running.', 'error');
          setError('Failed to load simulations');
        } else {
          setSimulations(r.simulations);
          setError(null);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load simulations';
        setError(message);
        addToast(message, 'error');
      } finally {
        setLoading(false);
      }
    };

    loadSimulations();
  }, [setSimulations, setLoading, setError, addToast]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  /** List API does not send started_at/completed_at; use created/updated as wall-clock span. */
  const formatSimulationDuration = (sim: (typeof simulations)[number]) => {
    // Not started yet — do not show created→now as a "runtime"
    if (sim.status === 'pending') return '-';
    const startIso = sim.startedAt ?? sim.createdAt;
    if (!startIso) return '-';
    const terminal =
      sim.status === 'completed' || sim.status === 'failed' || sim.status === 'cancelled';
    const endIso = sim.completedAt ?? (terminal ? sim.updatedAt : undefined);
    const start = new Date(startIso).getTime();
    const end = endIso ? new Date(endIso).getTime() : Date.now();
    const seconds = Math.max(0, Math.floor((end - start) / 1000));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m`;
    return `${seconds}s`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Simulations</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Manage and monitor your war-gaming scenarios
          </p>
        </div>
        <Link href="/simulations/new" className="w-full sm:w-auto">
          <Button leftIcon={<Plus className="w-4 h-4" />} className="w-full sm:w-auto">New Simulation</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="Search simulations..."
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>
        <Button variant="secondary" leftIcon={<Filter className="w-4 h-4" />}>
          Filter
        </Button>
      </div>

      {/* Bulk Actions Bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg bg-slate-800 border border-slate-700 px-4 py-3">
          <span className="text-sm text-slate-300">
            {selectedIds.size} selected
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={bulkDeleting}
            onClick={handleBulkDelete}
            className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            {bulkDeleting ? 'Deleting...' : 'Delete'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedIds(new Set())}
            leftIcon={<X className="w-4 h-4" />}
          >
            Clear
          </Button>
        </div>
      )}

      {/* Simulations Table */}
      <Card>
        {simulations.length > 0 ? (
          <div className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell isHeader className="w-10">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === simulations.length && simulations.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded border-slate-600 bg-slate-800 text-accent focus:ring-accent/50"
                    aria-label="Select all simulations"
                  />
                </TableCell>
                <TableCell isHeader>Name</TableCell>
                <TableCell isHeader>Playbook</TableCell>
                <TableCell isHeader>Status</TableCell>
                <TableCell isHeader>Agents</TableCell>
                <TableCell isHeader>Rounds</TableCell>
                <TableCell isHeader>Created</TableCell>
                <TableCell isHeader>Duration</TableCell>
                <TableCell isHeader>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {simulations.map((sim) => (
                <TableRow key={sim.id} hover className={selectedIds.has(sim.id) ? 'bg-accent/5' : ''}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(sim.id)}
                      onChange={() => toggleSelect(sim.id)}
                      className="rounded border-slate-600 bg-slate-800 text-accent focus:ring-accent/50"
                      aria-label={`Select simulation ${sim.name}`}
                    />
                  </TableCell>
                  <TableCell>
                    <span className="font-medium text-slate-200">{sim.name}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-slate-400">{sim.playbookName}</span>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={sim.status} size="sm" />
                  </TableCell>
                  <TableCell>
                    <span className="text-slate-300">{sim.agents?.length || 0}</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full"
                          style={{
                            width: `${(sim.currentRound / sim.totalRounds) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">
                        {sim.currentRound}/{sim.totalRounds}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-slate-400">{formatDate(sim.createdAt)}</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-slate-400">
                      <Clock className="w-3.5 h-3.5" />
                      <span className="text-sm">{formatSimulationDuration(sim)}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Link href={`/simulations/${sim.id}`}>
                        <Button variant="ghost" size="sm">
                          Monitor
                        </Button>
                      </Link>
                      {sim.status === 'completed' && (
                        <Link href={`/simulations/${sim.id}/report`}>
                          <Button variant="secondary" size="sm">
                            Report
                          </Button>
                        </Link>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletingId === sim.id}
                        onClick={() => handleDelete(sim.id, sim.name)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        ) : (
          <EmptyState
            title="No simulations yet"
            description={
              isLoading
                ? 'Loading…'
                : loadError
                  ? 'Could not load simulations from the server. Check that the backend is running.'
                  : 'Create your first war-gaming simulation to get started'
            }
            action={{
              label: 'Create Simulation',
              onClick: () => router.push('/simulations/new'),
            }}
          />
        )}
      </Card>
    </div>
  );
}
