'use client';

import { useEffect, useState } from 'react';
import { Plus, Settings, Play, CheckCircle, Clock, BarChart3, Activity, Trash2 } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { fetchApi } from '@/lib/api';

interface FineTuningJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  base_model: string;
  /** Training set size when known (from API `num_examples`). */
  dataset_size?: number;
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

function mapCreatedJobStatusToUi(raw: string): FineTuningJob['status'] {
  switch (raw) {
    case 'training':
      return 'running';
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    default:
      return 'pending';
  }
}

const PARSE_EPOCHS_MIN = 1;
const PARSE_EPOCHS_MAX = 10;

/** Parse epochs from a number input; never returns NaN (falls back to previous or 1). */
function parseEpochsInput(raw: string, previous: number): number {
  const parsed = parseInt(raw, 10);
  if (!Number.isNaN(parsed)) {
    return Math.min(
      PARSE_EPOCHS_MAX,
      Math.max(PARSE_EPOCHS_MIN, parsed),
    );
  }
  const fallback =
    Number.isFinite(previous) && previous >= 1 ? previous : 1;
  return Math.min(PARSE_EPOCHS_MAX, Math.max(PARSE_EPOCHS_MIN, fallback));
}

export default function FineTuningPage() {
  const { addToast } = useToast();
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [adapterToggleError, setAdapterToggleError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newJob, setNewJob] = useState({
    name: '',
    base_model: 'gpt-4',
    data_source: '',
    epochs: 3,
    learning_rate: 0.0001,
  });

  useEffect(() => {
    const loadFineTuningData = async () => {
      setIsLoading(true);
      try {
        const [jobsResult, adaptersResult] = await Promise.all([
          fetchApi<Array<{
            job_id: string;
            dataset_id: string;
            base_model: string;
            status: string;
            progress: number;
            created_at: string;
            completed_at?: string;
            num_examples?: number | null;
            metrics?: {
              loss?: number;
              accuracy?: number;
            };
          }>>('/api/llm/fine-tune/jobs'),
          fetchApi<Array<{
            adapter_id: string;
            job_id: string;
            base_model: string;
            domain: string;
            active: boolean;
            created_at: string;
            performance_metrics?: {
              accuracy?: number;
            };
          }>>('/api/llm/fine-tune/adapters'),
        ]);

        if (jobsResult.success && jobsResult.data) {
          setJobs(
            jobsResult.data.map((job) => ({
              id: job.job_id,
              name: `${job.base_model} adapter`,
              status:
                job.status === 'queued'
                  ? 'pending'
                  : job.status === 'training'
                  ? 'running'
                  : job.status === 'completed'
                  ? 'completed'
                  : 'failed',
              base_model: job.base_model,
              dataset_size:
                typeof job.num_examples === 'number' ? job.num_examples : undefined,
              progress: Math.round(job.progress),
              created_at: job.created_at,
              completed_at: job.completed_at,
              metrics: job.metrics?.loss !== undefined || job.metrics?.accuracy !== undefined
                ? {
                    loss: job.metrics?.loss ?? 0,
                    accuracy: job.metrics?.accuracy ?? 0,
                  }
                : undefined,
            }))
          );
        }

        if (adaptersResult.success && adaptersResult.data) {
          setAdapters(
            adaptersResult.data.map((adapter) => ({
              id: adapter.adapter_id,
              name: adapter.domain,
              job_id: adapter.job_id,
              is_active: adapter.active,
              created_at: adapter.created_at,
              performance_score: adapter.performance_metrics?.accuracy,
            }))
          );
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load fine-tuning data';
        console.error('[loadFineTuningData]', err);
        addToast(`${message}. Check that the API is running.`, 'error');
      } finally {
        setIsLoading(false);
      }
    };

    loadFineTuningData();
  }, [addToast]);

  const handleCreateJob = async () => {
    if (isCreating) return;
    setCreateError(null);
    setIsCreating(true);
    try {
      const preparedDataset = await fetchApi<{ dataset_id: string; num_examples: number }>('/api/llm/fine-tune/prepare-dataset', {
        method: 'POST',
        body: JSON.stringify({
          data_source: newJob.data_source,
          data_type: 'earnings_calls',
        }),
      });
      if (!preparedDataset.success || !preparedDataset.data) {
        const detail =
          preparedDataset.error ||
          preparedDataset.message ||
          (!preparedDataset.data ? 'No dataset in response.' : 'Request failed.');
        const msg = `Could not prepare dataset: ${detail}${preparedDataset.status != null ? ` (HTTP ${preparedDataset.status})` : ''}`;
        setCreateError(msg);
        addToast(msg, 'error');
        return;
      }

      const createdJob = await fetchApi<{
        job_id: string;
        base_model: string;
        status: string;
        progress: number;
        created_at: string;
      }>('/api/llm/fine-tune/start', {
        method: 'POST',
        body: JSON.stringify({
          dataset_id: preparedDataset.data.dataset_id,
          base_model: newJob.base_model,
          lora_config: {
            num_train_epochs: newJob.epochs,
            learning_rate: newJob.learning_rate,
          },
        }),
      });
      if (!createdJob.success || !createdJob.data) {
        const detail =
          createdJob.error ||
          createdJob.message ||
          (!createdJob.data ? 'No job in response.' : 'Request failed.');
        const msg = `Could not start training: ${detail}${createdJob.status != null ? ` (HTTP ${createdJob.status})` : ''}`;
        setCreateError(msg);
        addToast(msg, 'error');
        return;
      }

      const job: FineTuningJob = {
        id: createdJob.data.job_id,
        name: newJob.name || `${newJob.base_model} adapter`,
        status: mapCreatedJobStatusToUi(createdJob.data.status),
        base_model: createdJob.data.base_model,
        dataset_size: preparedDataset.data.num_examples,
        progress: Math.round(createdJob.data.progress),
        created_at: createdJob.data.created_at,
      };
      setJobs((prev) => [job, ...prev]);
      setShowCreateForm(false);
      setCreateError(null);
      setNewJob({ name: '', base_model: 'gpt-4', data_source: '', epochs: 3, learning_rate: 0.0001 });
    } catch (err) {
      console.error('[handleCreateJob]', err);
      const msg =
        err instanceof Error ? err.message : 'Failed to create fine-tuning job.';
      setCreateError(msg);
      addToast(msg, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleAdapter = async (adapterId: string) => {
    setAdapterToggleError(null);
    try {
      const result = await fetchApi<{ adapter_id: string }>(`/api/llm/fine-tune/activate/${adapterId}`, {
        method: 'POST',
      });
      if (!result.success || !result.data) {
        const detail =
          result.error ||
          result.message ||
          'Failed to activate adapter.';
        const msg = `${detail}${result.status != null ? ` (HTTP ${result.status})` : ''}`;
        setAdapterToggleError(msg);
        addToast(msg, 'error');
        return;
      }
      setAdapters((prev) =>
        prev.map((adapter) => ({
          ...adapter,
          is_active: adapter.id === adapterId,
        }))
      );
    } catch (err) {
      console.error('Adapter activation failed', err);
      const msg =
        err instanceof Error ? err.message : 'Failed to activate adapter.';
      setAdapterToggleError(msg);
      addToast(msg, 'error');
    }
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
          onClick={() => {
            setShowCreateForm((open) => {
              if (!open) setCreateError(null);
              return !open;
            });
          }}
        >
          New Fine-Tuning Job
        </Button>
      </div>

      {/* Create Job Form */}
      {showCreateForm && (
        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-100">Create New Fine-Tuning Job</h3>
            {createError && (
              <div
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300"
                role="alert"
              >
                {createError}
              </div>
            )}
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
                  onChange={(e) =>
                    setNewJob({
                      ...newJob,
                      epochs: parseEpochsInput(e.target.value, newJob.epochs),
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  min={1}
                  max={10}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setShowCreateForm(false);
                  setCreateError(null);
                }}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateJob} disabled={isCreating}>
                {isCreating ? 'Starting…' : 'Start Training'}
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
        {adapterToggleError && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {adapterToggleError}
          </div>
        )}
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
                      {job.base_model}
                      {typeof job.dataset_size === 'number' && !Number.isNaN(job.dataset_size)
                        ? ` • ${job.dataset_size.toLocaleString()} samples`
                        : ''}
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
