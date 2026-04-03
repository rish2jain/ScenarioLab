'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Settings, Play, Pause, CheckCircle, Clock, BarChart3, Trash2, Activity } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface FineTuningJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  base_model: string;
  dataset_size: number;
  progress: number;
  created_at: string;
  completed_at?: string;
  metrics?: {
    loss: number;
    accuracy: number;
  };
}

interface Adapter {
  id: string;
  name: string;
  job_id: string;
  is_active: boolean;
  created_at: string;
  performance_score?: number;
}

// Mock data
const mockJobs: FineTuningJob[] = [
  {
    id: 'job-1',
    name: 'M&A Scenario Adapter',
    status: 'completed',
    base_model: 'gpt-4',
    dataset_size: 1500,
    progress: 100,
    created_at: '2024-01-10T10:00:00Z',
    completed_at: '2024-01-10T14:30:00Z',
    metrics: {
      loss: 0.23,
      accuracy: 0.89,
    },
  },
  {
    id: 'job-2',
    name: 'Boardroom Negotiation',
    status: 'running',
    base_model: 'claude-3',
    dataset_size: 2300,
    progress: 67,
    created_at: '2024-01-15T08:00:00Z',
    metrics: {
      loss: 0.31,
      accuracy: 0.84,
    },
  },
  {
    id: 'job-3',
    name: 'Crisis Response Model',
    status: 'pending',
    base_model: 'gpt-4',
    dataset_size: 800,
    progress: 0,
    created_at: '2024-01-16T09:00:00Z',
  },
];

const mockAdapters: Adapter[] = [
  {
    id: 'adapter-1',
    name: 'M&A Scenario Adapter',
    job_id: 'job-1',
    is_active: true,
    created_at: '2024-01-10T14:30:00Z',
    performance_score: 0.92,
  },
  {
    id: 'adapter-2',
    name: 'Boardroom Negotiation',
    job_id: 'job-2',
    is_active: false,
    created_at: '2024-01-15T08:00:00Z',
    performance_score: 0.78,
  },
];

export default function FineTuningPage() {
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newJob, setNewJob] = useState({
    name: '',
    base_model: 'gpt-4',
    data_source: '',
    epochs: 3,
    learning_rate: 0.0001,
  });

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      // Mock API calls
      setJobs(mockJobs);
      setAdapters(mockAdapters);
      setIsLoading(false);
    };

    loadData();
  }, []);

  const handleCreateJob = async () => {
    // Mock creation
    const job: FineTuningJob = {
      id: `job-${Date.now()}`,
      name: newJob.name,
      status: 'pending',
      base_model: newJob.base_model,
      dataset_size: 0,
      progress: 0,
      created_at: new Date().toISOString(),
    };
    setJobs([job, ...jobs]);
    setShowCreateForm(false);
    setNewJob({ name: '', base_model: 'gpt-4', data_source: '', epochs: 3, learning_rate: 0.0001 });
  };

  const handleToggleAdapter = (adapterId: string) => {
    setAdapters(adapters.map(a =>
      a.id === adapterId ? { ...a, is_active: !a.is_active } : a
    ));
  };

  const handleDeleteAdapter = (adapterId: string) => {
    setAdapters(adapters.filter(a => a.id !== adapterId));
  };

  const getStatusIcon = (status: FineTuningJob['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'running':
        return <Activity className="w-5 h-5 text-accent animate-pulse" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-400" />;
      case 'failed':
        return <Trash2 className="w-5 h-5 text-red-400" />;
    }
  };

  const getStatusClass = (status: FineTuningJob['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400';
      case 'running':
        return 'bg-accent/20 text-accent';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'failed':
        return 'bg-red-500/20 text-red-400';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading fine-tuning jobs...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Fine-Tuning Management</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Manage custom model adapters and training jobs
          </p>
        </div>
        <Button
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          New Fine-Tuning Job
        </Button>
      </div>

      {/* Create Job Form */}
      {showCreateForm && (
        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-100">Create New Fine-Tuning Job</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Job Name</label>
                <input
                  type="text"
                  value={newJob.name}
                  onChange={(e) => setNewJob({ ...newJob, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  placeholder="e.g., M&A Scenario Adapter"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Base Model</label>
                <select
                  value={newJob.base_model}
                  onChange={(e) => setNewJob({ ...newJob, base_model: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                >
                  <option value="gpt-4">GPT-4</option>
                  <option value="claude-3">Claude 3</option>
                  <option value="gpt-3.5">GPT-3.5</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Data Source</label>
                <input
                  type="text"
                  value={newJob.data_source}
                  onChange={(e) => setNewJob({ ...newJob, data_source: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  placeholder="Dataset ID or file path"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Epochs</label>
                <input
                  type="number"
                  value={newJob.epochs}
                  onChange={(e) => setNewJob({ ...newJob, epochs: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  min={1}
                  max={10}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateJob}>
                Start Training
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Active Adapters */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-100">Active Adapters</h2>
          </div>
        }
      >
        <div className="space-y-3">
          {adapters.map((adapter) => (
            <div key={adapter.id} className="flex items-center justify-between p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  adapter.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600/20 text-slate-400'
                }`}>
                  <Settings className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-medium text-slate-200">{adapter.name}</div>
                  <div className="text-sm text-slate-500">
                    Created {new Date(adapter.created_at).toLocaleDateString()}
                    {adapter.performance_score && ` • Score: ${(adapter.performance_score * 100).toFixed(0)}%`}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggleAdapter(adapter.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    adapter.is_active
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-slate-600/20 text-slate-400 hover:bg-slate-600/40'
                  }`}
                >
                  {adapter.is_active ? 'Active' : 'Inactive'}
                </button>
                <button
                  onClick={() => handleDeleteAdapter(adapter.id)}
                  className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
          {adapters.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No adapters created yet
            </div>
          )}
        </div>
      </Card>

      {/* Training Jobs */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-100">Training Jobs</h2>
          </div>
        }
      >
        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  {getStatusIcon(job.status)}
                  <div>
                    <div className="font-medium text-slate-200">{job.name}</div>
                    <div className="text-sm text-slate-500">
                      {job.base_model} • {job.dataset_size.toLocaleString()} samples
                    </div>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusClass(job.status)}`}>
                  {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-400">Progress</span>
                  <span className="text-slate-300">{job.progress}%</span>
                </div>
                <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>

              {/* Metrics */}
              {job.metrics && (
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <BarChart3 className="w-4 h-4 text-slate-500" />
                    <span className="text-slate-400">Loss:</span>
                    <span className="text-slate-300">{job.metrics.loss.toFixed(4)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-slate-500" />
                    <span className="text-slate-400">Accuracy:</span>
                    <span className="text-slate-300">{(job.metrics.accuracy * 100).toFixed(1)}%</span>
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="mt-3 text-xs text-slate-500">
                Created: {new Date(job.created_at).toLocaleString()}
                {job.completed_at && ` • Completed: ${new Date(job.completed_at).toLocaleString()}`}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
