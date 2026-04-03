'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Key, Trash2, Copy, Check, Webhook, Globe } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ApiKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  created_at: string;
  last_used?: string;
}

interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

// Mock data
const mockApiKeys: ApiKey[] = [
  {
    id: 'key-1',
    name: 'Production API Key',
    key: 'mf_live_xxxxxxxxxxxx1234',
    permissions: ['read', 'write', 'simulate'],
    created_at: '2024-01-10T10:00:00Z',
    last_used: '2024-01-16T14:30:00Z',
  },
  {
    id: 'key-2',
    name: 'Development Key',
    key: 'mf_dev_xxxxxxxxxxxx5678',
    permissions: ['read', 'write'],
    created_at: '2024-01-15T08:00:00Z',
    last_used: '2024-01-16T09:15:00Z',
  },
];

const mockWebhooks: Webhook[] = [
  {
    id: 'wh-1',
    url: 'https://api.example.com/webhooks/mirofish',
    events: ['simulation.completed', 'report.generated'],
    is_active: true,
    created_at: '2024-01-12T10:00:00Z',
  },
];

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [showWebhookForm, setShowWebhookForm] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [newKey, setNewKey] = useState({ name: '', permissions: ['read'] });
  const [newWebhook, setNewWebhook] = useState({ url: '', events: ['simulation.completed'] });

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setApiKeys(mockApiKeys);
      setWebhooks(mockWebhooks);
      setIsLoading(false);
    };

    loadData();
  }, []);

  const handleCreateKey = async () => {
    const key: ApiKey = {
      id: `key-${Date.now()}`,
      name: newKey.name,
      key: `mf_live_${Math.random().toString(36).substring(2, 15)}`,
      permissions: newKey.permissions,
      created_at: new Date().toISOString(),
    };
    setApiKeys([key, ...apiKeys]);
    setShowKeyForm(false);
    setNewKey({ name: '', permissions: ['read'] });
  };

  const handleRevokeKey = (keyId: string) => {
    setApiKeys(apiKeys.filter(k => k.id !== keyId));
  };

  const handleCopyKey = (key: string, id: string) => {
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreateWebhook = async () => {
    const webhook: Webhook = {
      id: `wh-${Date.now()}`,
      url: newWebhook.url,
      events: newWebhook.events,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    setWebhooks([webhook, ...webhooks]);
    setShowWebhookForm(false);
    setNewWebhook({ url: '', events: ['simulation.completed'] });
  };

  const handleDeleteWebhook = (webhookId: string) => {
    setWebhooks(webhooks.filter(w => w.id !== webhookId));
  };

  const togglePermission = (permission: string) => {
    setNewKey(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission],
    }));
  };

  const toggleEvent = (event: string) => {
    setNewWebhook(prev => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter(e => e !== event)
        : [...prev.events, event],
    }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading API keys...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">API Key Management</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Manage API keys and webhook integrations
          </p>
        </div>
      </div>

      {/* API Keys Section */}
      <Card
        header={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-semibold text-slate-100">API Keys</h2>
            </div>
            <Button
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setShowKeyForm(!showKeyForm)}
            >
              Generate Key
            </Button>
          </div>
        }
      >
        {/* Create Key Form */}
        {showKeyForm && (
          <div className="mb-6 p-4 bg-slate-700/20 rounded-lg">
            <h3 className="font-medium text-slate-200 mb-4">Generate New API Key</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Key Name</label>
                <input
                  type="text"
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                  placeholder="e.g., Production API Key"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Permissions</label>
                <div className="flex flex-wrap gap-2">
                  {['read', 'write', 'simulate', 'admin'].map((permission) => (
                    <button
                      key={permission}
                      onClick={() => togglePermission(permission)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        newKey.permissions.includes(permission)
                          ? 'bg-accent text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {permission.charAt(0).toUpperCase() + permission.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setShowKeyForm(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleCreateKey}>
                  Generate
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Keys List */}
        <div className="space-y-3">
          {apiKeys.map((key) => (
            <div key={key.id} className="flex items-center justify-between p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                  <Key className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <div className="font-medium text-slate-200">{key.name}</div>
                  <div className="text-sm text-slate-500">
                    {key.key.substring(0, 12)}... • Created {new Date(key.created_at).toLocaleDateString()}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {key.permissions.map((perm) => (
                      <span key={perm} className="px-1.5 py-0.5 bg-slate-600/30 rounded text-xs text-slate-400">
                        {perm}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopyKey(key.key, key.id)}
                  className="p-2 text-slate-400 hover:text-slate-200 transition-colors"
                  title="Copy key"
                >
                  {copiedId === key.id ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => handleRevokeKey(key.id)}
                  className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                  title="Revoke key"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
          {apiKeys.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No API keys generated yet
            </div>
          )}
        </div>
      </Card>

      {/* Webhooks Section */}
      <Card
        header={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-semibold text-slate-100">Webhooks</h2>
            </div>
            <Button
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setShowWebhookForm(!showWebhookForm)}
            >
              Add Webhook
            </Button>
          </div>
        }
      >
        {/* Create Webhook Form */}
        {showWebhookForm && (
          <div className="mb-6 p-4 bg-slate-700/20 rounded-lg">
            <h3 className="font-medium text-slate-200 mb-4">Register New Webhook</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Webhook URL</label>
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-slate-500" />
                  <input
                    type="url"
                    value={newWebhook.url}
                    onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })}
                    className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
                    placeholder="https://api.example.com/webhooks/mirofish"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Events</label>
                <div className="flex flex-wrap gap-2">
                  {['simulation.completed', 'simulation.started', 'report.generated', 'annotation.added'].map((event) => (
                    <button
                      key={event}
                      onClick={() => toggleEvent(event)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        newWebhook.events.includes(event)
                          ? 'bg-accent text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {event}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setShowWebhookForm(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleCreateWebhook}>
                  Register
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Webhooks List */}
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="flex items-center justify-between p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  webhook.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600/20 text-slate-400'
                }`}>
                  <Webhook className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-medium text-slate-200">{webhook.url}</div>
                  <div className="text-sm text-slate-500">
                    Created {new Date(webhook.created_at).toLocaleDateString()}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {webhook.events.map((event) => (
                      <span key={event} className="px-1.5 py-0.5 bg-slate-600/30 rounded text-xs text-slate-400">
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  webhook.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600/20 text-slate-400'
                }`}>
                  {webhook.is_active ? 'Active' : 'Inactive'}
                </span>
                <button
                  onClick={() => handleDeleteWebhook(webhook.id)}
                  className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                  title="Delete webhook"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
          {webhooks.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No webhooks registered yet
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
