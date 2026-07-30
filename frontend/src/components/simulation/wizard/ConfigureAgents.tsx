'use client';

import { Plus, Minus } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import type { Playbook } from '@/lib/types';

export interface ConfigureAgentsProps {
  selectedPlaybook: Playbook;
  agentConfigs: Record<string, number>;
  updateAgentCount: (role: string, delta: number) => void;
  totalAgents: number;
}

export function ConfigureAgents({
  selectedPlaybook,
  agentConfigs,
  updateAgentCount,
  totalAgents,
}: ConfigureAgentsProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Configure Agents</h2>
        <p className="text-foreground-muted mt-1">
          Adjust the number of agents for each role in your simulation
        </p>
      </div>
      <div className="space-y-4">
        {(selectedPlaybook.roster ?? []).map((role) => (
          <div
            key={role.role}
            className="flex items-center justify-between p-4 bg-background-secondary/50 rounded-lg border border-border"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-foreground">{role.role}</h4>
                {role.required && (
                  <Badge variant="info" size="sm">
                    Required
                  </Badge>
                )}
              </div>
              <p className="text-sm text-foreground-muted mt-1">{role.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="default" size="sm">
                  {role.archetype}
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label={`Decrease ${role.role} count`}
                onClick={() => updateAgentCount(role.role, -1)}
                disabled={(agentConfigs[role.role] ?? 0) <= 0}
                className="w-8 h-8 rounded-lg bg-background-tertiary flex items-center justify-center text-foreground-muted hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span aria-live="polite" className="w-8 text-center font-medium text-foreground">
                {agentConfigs[role.role] || 0}
              </span>
              <button
                type="button"
                aria-label={`Increase ${role.role} count`}
                onClick={() => updateAgentCount(role.role, 1)}
                className="w-8 h-8 rounded-lg bg-background-tertiary flex items-center justify-center text-foreground-muted hover:bg-border"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="p-4 bg-background-secondary/30 rounded-lg border border-border">
        <div className="flex items-center justify-between">
          <span className="text-foreground-muted">Total Agents</span>
          <span className="text-xl font-semibold text-foreground">{totalAgents}</span>
        </div>
      </div>
    </div>
  );
}
