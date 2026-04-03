'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import {
  Activity,
  TrendingUp,
  BookOpen,
  Play,
  Plus,
  Upload,
  FileText,
  ChevronRight,
  Clock,
  Users,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Table, TableHead, TableBody, TableRow, TableCell } from '@/components/ui/Table';
import { useSimulationStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { Simulation, DashboardStats } from '@/lib/types';

// Mock stats
const stats: DashboardStats = {
  totalSimulations: 12,
  activeSimulations: 2,
  reportsGenerated: 8,
  playbooksAvailable: 4,
};

// Mock recent simulations
const recentSimulations: Simulation[] = [
  {
    id: 'sim-1',
    name: 'TechCorp Acquisition Analysis',
    playbookId: 'pb-1',
    playbookName: 'M&A Culture Clash',
    status: 'completed',
    agents: [],
    config: { rounds: 12, environmentType: 'corporate', modelSelection: 'gpt-4' },
    currentRound: 12,
    totalRounds: 12,
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'sim-2',
    name: 'GDPR Compliance Crisis',
    playbookId: 'pb-2',
    playbookName: 'Regulatory Shock Test',
    status: 'running',
    agents: [],
    config: { rounds: 10, environmentType: 'crisis', modelSelection: 'gpt-4' },
    currentRound: 6,
    totalRounds: 10,
    createdAt: '2024-01-16T14:00:00Z',
  },
  {
    id: 'sim-3',
    name: 'Q1 Competitive Scenario',
    playbookId: 'pb-3',
    playbookName: 'Competitive Response',
    status: 'paused',
    agents: [],
    config: { rounds: 15, environmentType: 'market', modelSelection: 'claude-3' },
    currentRound: 8,
    totalRounds: 15,
    createdAt: '2024-01-14T09:00:00Z',
  },
];

export default function DashboardPage() {
  const setSimulations = useSimulationStore((state) => state.setSimulations);

  useEffect(() => {
    // Load mock data
    setSimulations(recentSimulations);
  }, [setSimulations]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">Dashboard</h1>
          <p className="text-foreground-muted mt-1 text-sm sm:text-base">
            Welcome to MiroFish - Your AI war-gaming command center
          </p>
        </div>
        <Link href="/simulations/new" className="w-full sm:w-auto">
          <Button leftIcon={<Plus className="w-4 h-4" />} className="w-full sm:w-auto">
            New Simulation
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Simulations"
          value={stats.totalSimulations}
          icon={<Activity className="w-5 h-5" />}
          trend="+3 this week"
          trendUp={true}
        />
        <StatCard
          title="Active Simulations"
          value={stats.activeSimulations}
          icon={<Play className="w-5 h-5" />}
          trend="Currently running"
          trendUp={true}
          highlight
        />
        <StatCard
          title="Reports Generated"
          value={stats.reportsGenerated}
          icon={<FileText className="w-5 h-5" />}
          trend="Ready for review"
          trendUp={true}
        />
        <StatCard
          title="Playbooks Available"
          value={stats.playbooksAvailable}
          icon={<BookOpen className="w-5 h-5" />}
          trend="Templates ready"
          trendUp={false}
        />
      </div>

      {/* Recent Simulations */}
      <Card
        header={
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-foreground">
              Recent Simulations
            </h2>
            <Link
              href="/simulations"
              className="text-sm text-accent hover:text-accent-light flex items-center gap-1"
            >
              View all <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        }
      >
        <div className="overflow-x-auto">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell isHeader>Name</TableCell>
              <TableCell isHeader>Playbook</TableCell>
              <TableCell isHeader>Status</TableCell>
              <TableCell isHeader>Progress</TableCell>
              <TableCell isHeader>Created</TableCell>
              <TableCell isHeader>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {recentSimulations.map((sim) => (
              <TableRow key={sim.id} hover>
                <TableCell>
                  <span className="font-medium text-foreground">{sim.name}</span>
                </TableCell>
                <TableCell>
                  <span className="text-foreground-muted">{sim.playbookName}</span>
                </TableCell>
                <TableCell>
                  <StatusBadge status={sim.status} size="sm" />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-accent to-accent-purple rounded-full"
                        style={{
                          width: `${(sim.currentRound / sim.totalRounds) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-foreground-muted">
                      {sim.currentRound}/{sim.totalRounds}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-foreground-muted">{formatDate(sim.createdAt)}</span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Link href={`/simulations/${sim.id}`}>
                      <Button variant="ghost" size="sm">
                        View
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
      </Card>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard
            title="New Simulation"
            description="Start a war-gaming scenario"
            icon={<Play className="w-6 h-6" />}
            href="/simulations/new"
            color="accent"
          />
          <QuickActionCard
            title="Upload Seeds"
            description="Import strategic documents"
            icon={<Upload className="w-6 h-6" />}
            href="/upload"
            color="blue"
          />
          <QuickActionCard
            title="Browse Playbooks"
            description="Explore simulation templates"
            icon={<BookOpen className="w-6 h-6" />}
            href="/playbooks"
            color="purple"
          />
          <QuickActionCard
            title="View Reports"
            description="Access generated insights"
            icon={<FileText className="w-6 h-6" />}
            href="/reports"
            color="green"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  trend,
  trendUp,
  highlight = false,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  trend: string;
  trendUp?: boolean;
  highlight?: boolean;
}) {
  return (
    <Card
      className={highlight ? 'border-accent/30' : ''}
      padding="lg"
    >
      <div className="flex items-start justify-between">
        <div
          className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center shadow-sm',
            highlight ? 'bg-accent/10 text-accent' : 'bg-background-tertiary text-foreground-subtle'
          )}
        >
          {icon}
        </div>
        {trendUp !== undefined && (
          <span
              className={clsx(
                'text-xs font-medium',
                trendUp ? 'text-success' : 'text-foreground-muted'
              )}
          >
            {trend}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-300">{value}</p>
        <p className="text-sm text-foreground-muted mt-1">{title}</p>
      </div>
    </Card>
  );
}

function QuickActionCard({
  title,
  description,
  icon,
  href,
  color,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  color: 'accent' | 'blue' | 'purple' | 'green';
}) {
  const colorClasses = {
    accent: 'bg-accent/5 text-accent border-accent/20 hover:border-accent/40 hover:shadow-lg hover:shadow-accent/10',
    blue: 'bg-info/5 text-info border-info/20 hover:border-info/40 hover:shadow-lg hover:shadow-info/10',
    purple: 'bg-purple-500/5 text-purple-400 border-purple-500/20 hover:border-purple-500/40 hover:shadow-lg hover:shadow-purple-500/10',
    green: 'bg-success/5 text-success border-success/20 hover:border-success/40 hover:shadow-lg hover:shadow-success/10',
  };

  return (
    <Link href={href}>
      <Card
        hover
        className={clsx('h-full border-2 transition-all', colorClasses[color])}
        padding="lg"
      >
        <div className="flex flex-col h-full">
          <div className="w-12 h-12 rounded-lg bg-background-secondary/80 flex items-center justify-center mb-4 backdrop-blur-sm border border-white/5">
            {icon}
          </div>
          <h3 className="font-semibold text-foreground">{title}</h3>
          <p className="text-sm text-foreground-muted mt-1">{description}</p>
        </div>
      </Card>
    </Link>
  );
}

import { clsx } from 'clsx';
