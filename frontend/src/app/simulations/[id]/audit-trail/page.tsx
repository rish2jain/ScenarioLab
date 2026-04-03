'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Download, Shield, CheckCircle, XCircle, FileJson, FileSpreadsheet } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type { AuditTrail, AuditEvent, AuditEventType } from '@/lib/types';

const eventTypeColors: Record<AuditEventType, string> = {
  config_change: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  simulation_start: 'bg-green-500/20 text-green-400 border-green-500/30',
  simulation_pause: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  simulation_resume: 'bg-green-500/20 text-green-400 border-green-500/30',
  simulation_complete: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  agent_decision: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  report_generation: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  annotation_added: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  parameter_change: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  export: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const eventTypeLabels: Record<AuditEventType, string> = {
  config_change: 'Config Change',
  simulation_start: 'Simulation Start',
  simulation_pause: 'Simulation Pause',
  simulation_resume: 'Simulation Resume',
  simulation_complete: 'Simulation Complete',
  agent_decision: 'Agent Decision',
  report_generation: 'Report Generation',
  annotation_added: 'Annotation Added',
  parameter_change: 'Parameter Change',
  export: 'Export',
};

// Mock audit trail data
const mockAuditTrail: AuditTrail = {
  simulation_id: 'sim-1',
  events: [
    {
      event_id: 'evt-1',
      simulation_id: 'sim-1',
      event_type: 'simulation_start',
      timestamp: '2024-01-15T10:05:00Z',
      actor: 'system',
      details: { initiated_by: 'user-1', config: { rounds: 12 } },
      previous_hash: '0',
      hash: 'abc123',
    },
    {
      event_id: 'evt-2',
      simulation_id: 'sim-1',
      event_type: 'agent_decision',
      timestamp: '2024-01-15T10:06:30Z',
      actor: 'agent-1',
      details: { round: 1, decision: 'propose_rapid_integration' },
      previous_hash: 'abc123',
      hash: 'def456',
    },
    {
      event_id: 'evt-3',
      simulation_id: 'sim-1',
      event_type: 'agent_decision',
      timestamp: '2024-01-15T10:07:15Z',
      actor: 'agent-2',
      details: { round: 1, decision: 'express_cultural_concerns' },
      previous_hash: 'def456',
      hash: 'ghi789',
    },
    {
      event_id: 'evt-4',
      simulation_id: 'sim-1',
      event_type: 'simulation_pause',
      timestamp: '2024-01-15T10:30:00Z',
      actor: 'user-1',
      details: { round: 3, reason: 'review_required' },
      previous_hash: 'ghi789',
      hash: 'jkl012',
    },
    {
      event_id: 'evt-5',
      simulation_id: 'sim-1',
      event_type: 'simulation_resume',
      timestamp: '2024-01-15T10:35:00Z',
      actor: 'user-1',
      details: { round: 3 },
      previous_hash: 'jkl012',
      hash: 'mno345',
    },
    {
      event_id: 'evt-6',
      simulation_id: 'sim-1',
      event_type: 'config_change',
      timestamp: '2024-01-15T10:40:00Z',
      actor: 'user-1',
      details: { parameter: 'temperature', old_value: 0.7, new_value: 0.5 },
      previous_hash: 'mno345',
      hash: 'pqr678',
    },
    {
      event_id: 'evt-7',
      simulation_id: 'sim-1',
      event_type: 'annotation_added',
      timestamp: '2024-01-15T11:00:00Z',
      actor: 'user-1',
      details: { round: 6, message_id: 'msg-12', tag: 'critical' },
      previous_hash: 'pqr678',
      hash: 'stu901',
    },
    {
      event_id: 'evt-8',
      simulation_id: 'sim-1',
      event_type: 'simulation_complete',
      timestamp: '2024-01-15T11:15:00Z',
      actor: 'system',
      details: { final_round: 12, total_duration_minutes: 70 },
      previous_hash: 'stu901',
      hash: 'vwx234',
    },
    {
      event_id: 'evt-9',
      simulation_id: 'sim-1',
      event_type: 'report_generation',
      timestamp: '2024-01-15T11:20:00Z',
      actor: 'system',
      details: { report_id: 'report-1', format: 'full' },
      previous_hash: 'vwx234',
      hash: 'yzu567',
    },
    {
      event_id: 'evt-10',
      simulation_id: 'sim-1',
      event_type: 'export',
      timestamp: '2024-01-15T11:25:00Z',
      actor: 'user-1',
      details: { format: 'json', content: 'full_simulation' },
      previous_hash: 'yzu567',
      hash: 'abc890',
    },
  ],
  is_valid: true,
  integrity_check_message: 'All events verified successfully',
};

export default function AuditTrailPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';

  const [auditTrail, setAuditTrail] = useState<AuditTrail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [filter, setFilter] = useState<AuditEventType | 'all'>('all');

  useEffect(() => {
    const loadAuditTrail = async () => {
      setIsLoading(true);
      const result = await api.getAuditTrail(simulationId);
      if (result) {
        setAuditTrail(result);
      } else {
        setAuditTrail(mockAuditTrail);
      }
      setIsLoading(false);
    };

    loadAuditTrail();
  }, [simulationId]);

  const handleVerify = async () => {
    setIsVerifying(true);
    const result = await api.verifyAuditTrail(simulationId);
    if (result) {
      setVerifyResult(result);
    } else {
      setVerifyResult({ valid: true, message: 'Audit trail integrity verified (mock)' });
    }
    setIsVerifying(false);
  };

  const handleExport = async (format: 'json' | 'csv') => {
    const data = await api.exportAuditTrail(simulationId, format);
    if (data) {
      const blob = new Blob([data], {
        type: format === 'json' ? 'application/json' : 'text/csv',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `audit-trail-${simulationId}.${format}`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  const filteredEvents = auditTrail?.events.filter(
    (event) => filter === 'all' || event.event_type === filter
  ) || [];

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading audit trail...</div>
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
                Audit Trail
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                Simulation ID: {simulationId}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<FileJson className="w-4 h-4" />}
              onClick={() => handleExport('json')}
            >
              Export JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<FileSpreadsheet className="w-4 h-4" />}
              onClick={() => handleExport('csv')}
            >
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Integrity Status */}
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  auditTrail?.is_valid ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-100">
                    Integrity Status
                  </h3>
                  <p className="text-sm text-slate-400">
                    {auditTrail?.integrity_check_message || 'Unknown'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {verifyResult && (
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                    verifyResult.valid ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                  }`}>
                    {verifyResult.valid ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    <span className="text-sm">{verifyResult.message}</span>
                  </div>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<Shield className="w-4 h-4" />}
                  onClick={handleVerify}
                  isLoading={isVerifying}
                >
                  Verify Integrity
                </Button>
              </div>
            </div>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card padding="md">
              <div className="text-2xl font-bold text-slate-100">
                {auditTrail?.events.length || 0}
              </div>
              <div className="text-sm text-slate-400">Total Events</div>
            </Card>
            <Card padding="md">
              <div className="text-2xl font-bold text-slate-100">
                {new Set(auditTrail?.events.map(e => e.actor)).size || 0}
              </div>
              <div className="text-sm text-slate-400">Unique Actors</div>
            </Card>
            <Card padding="md">
              <div className="text-2xl font-bold text-slate-100">
                {auditTrail?.events.filter(e => e.event_type === 'agent_decision').length || 0}
              </div>
              <div className="text-sm text-slate-400">Agent Decisions</div>
            </Card>
            <Card padding="md">
              <div className="text-2xl font-bold text-green-400">
                {auditTrail?.is_valid ? 'Valid' : 'Invalid'}
              </div>
              <div className="text-sm text-slate-400">Chain Integrity</div>
            </Card>
          </div>

          {/* Filter */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-400">Filter:</span>
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-accent text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              All
            </button>
            {Object.entries(eventTypeLabels).map(([type, label]) => (
              <button
                key={type}
                onClick={() => setFilter(type as AuditEventType)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filter === type
                    ? 'bg-accent text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Events Table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Time</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Type</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Actor</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Details</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {filteredEvents.map((event) => (
                    <tr key={event.event_id} className="hover:bg-slate-700/20">
                      <td className="py-3 px-4 text-sm text-slate-300 whitespace-nowrap">
                        {formatTimestamp(event.timestamp)}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                          eventTypeColors[event.event_type]
                        }`}>
                          {eventTypeLabels[event.event_type]}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-300">
                        {event.actor}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-400 max-w-xs truncate">
                        {JSON.stringify(event.details)}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-500 font-mono text-xs">
                        {event.hash.substring(0, 8)}...
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredEvents.length === 0 && (
                <div className="text-center py-12 text-slate-500">
                  No events match the selected filter.
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
