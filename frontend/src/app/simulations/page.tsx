'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, Search, Filter, ChevronRight, Clock } from 'lucide-react';
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
import { api } from '@/lib/api';

export default function SimulationsPage() {
  const router = useRouter();
  const { simulations, setSimulations, isLoading, setLoading, setError } = useSimulationStore();

  useEffect(() => {
    const loadSimulations = async () => {
      setLoading(true);
      try {
        const data = await api.getSimulations();
        setSimulations(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load simulations';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    loadSimulations();
  }, [setSimulations, setLoading, setError]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
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

      {/* Simulations Table */}
      <Card>
        {simulations.length > 0 ? (
          <div className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow>
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
                <TableRow key={sim.id} hover>
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
                      <span className="text-sm">{formatDuration(sim.elapsedTime)}</span>
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
            description="Create your first war-gaming simulation to get started"
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
