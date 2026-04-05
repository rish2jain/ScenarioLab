'use client';

import { useEffect, useState } from 'react';
import { Plus, Key, Trash2, Copy, Check, Webhook, Globe } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { fetchApi } from '@/lib/api';
import {
  adminAuthHeaders,
  clearAdminApiKey,
  getAdminApiKey,
  setAdminApiKey,
} from '@/lib/adminApiKey';

/** Persisted after key creation so webhook list can use GET /webhooks (requires X-API-Key). */
const INTEGRATION_KEY_STORAGE = 'scenariolab_integration_api_key';

interface StoredIntegrationKey {
  keyId: string;
  secret: string;
}

function readStoredIntegrationKey(): StoredIntegrationKey | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(INTEGRATION_KEY_STORAGE);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredIntegrationKey;
    if (parsed?.keyId && typeof parsed.secret === 'string' && parsed.secret.length > 0) {
      return parsed;
    }
  } catch {
    /* ignore */
  }
  return null;
}

function writeStoredIntegrationKey(key: StoredIntegrationKey) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(INTEGRATION_KEY_STORAGE, JSON.stringify(key));
}

function clearStoredIntegrationKey() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(INTEGRATION_KEY_STORAGE);
}

interface ApiKey {
  key_id: string;
  name: string;
  key: string;
  permissions: string[];
  created_at: string;
  last_used_at?: string | null;
  active?: boolean;
}

/** Matches backend `app.api_integrations.webhooks.Webhook` (snake_case JSON). */
interface Webhook {
  webhook_id: string;
  url: string;
  events: string[];
  api_key_id: string;
  active: boolean;
  created_at: string;
  last_triggered_at?: string | null;
  failure_count?: number;
  metadata?: Record<string, unknown>;
}

/** Must match backend `WEBHOOK_EVENT_TYPES` in `app/api_integrations/webhooks.py`. */
const WEBHOOK_EVENT_OPTIONS = [
  'simulation_started',
  'simulation_completed',
  'simulation_failed',
  'report_generated',
] as const;

/** Permission scopes shown in the create-key form (subset of strings used with `require_permission` on the API). */
const API_KEY_PERMISSION_OPTIONS = [
  'read:simulations',
  'write:simulations',
  'read:reports',
  'write:reports',
] as const;

/** Full secret is only in sessionStorage for the key created in this tab; list API returns masked `key`. */
function getFullSecretForKeyId(keyId: string): string | null {
  const stored = readStoredIntegrationKey();
  if (stored?.keyId === keyId && stored.secret.length > 0) {
    return stored.secret;
  }
  return null;
}

export default function ApiKeysPage() {
  const { addToast } = useToast();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [isLoading, setIsLoading] = useState(() => !!getAdminApiKey());
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [showWebhookForm, setShowWebhookForm] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [newKey, setNewKey] = useState<{ name: string; permissions: string[] }>({
    name: '',
    permissions: [API_KEY_PERMISSION_OPTIONS[0]],
  });
  const [newWebhook, setNewWebhook] = useState({ url: '', events: ['simulation_completed'] });
  const [sessionApiKey, setSessionApiKey] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [createKeyError, setCreateKeyError] = useState<string | null>(null);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [adminUnlocked, setAdminUnlocked] = useState(() => !!getAdminApiKey());
  const [adminInput, setAdminInput] = useState('');
  const [adminGateError, setAdminGateError] = useState<string | null>(null);

  useEffect(() => {
    if (!adminUnlocked) {
      queueMicrotask(() => setIsLoading(false));
      return;
    }

    const loadData = async () => {
      setIsLoading(true);
      setPageError(null);

      const keysResult = await fetchApi<ApiKey[]>('/api/v1/api-keys', {
        headers: adminAuthHeaders(),
      });
      if (keysResult.success && keysResult.data) {
        setApiKeys(keysResult.data);
      }
      if (!keysResult.success) {
        if (keysResult.status === 503) {
          setPageError(
            'API key management is disabled on the server. Set ADMIN_API_KEY in the backend environment and restart.',
          );
        } else if (keysResult.status === 401 || keysResult.status === 403) {
          setPageError('Invalid admin key. Clear it and sign in again with the value of ADMIN_API_KEY.');
        } else {
          setPageError('Failed to load API keys from API');
        }
      }

      // GET /api/v1/webhooks requires X-API-Key; only call after we have a secret (sessionStorage).
      const stored = readStoredIntegrationKey();
      if (stored) {
        setSessionApiKey(stored.secret);
        const webhooksResult = await fetchApi<Webhook[]>('/api/v1/webhooks', {
          headers: { 'X-API-Key': stored.secret },
        });
        if (webhooksResult.success && webhooksResult.data) {
          setWebhooks(webhooksResult.data);
        } else if (webhooksResult.status === 401) {
          clearStoredIntegrationKey();
          setSessionApiKey(null);
          setWebhooks([]);
        }
      } else {
        setWebhooks([]);
      }

      setIsLoading(false);
    };

    void loadData();
  }, [adminUnlocked]);

  const handleCreateKey = async () => {
    if (!newKey.name || newKey.name.trim().length === 0) {
      return;
    }
    setCreateKeyError(null);
    const result = await fetchApi<ApiKey>('/api/v1/api-keys', {
      method: 'POST',
      headers: adminAuthHeaders(),
      body: JSON.stringify(newKey),
    });
    if (!result.success || !result.data) {
      const detail =
        result.error ||
        result.message ||
        'Failed to create API key.';
      setCreateKeyError(detail);
      return;
    }

    const created = result.data;
    setCreateKeyError(null);
    setApiKeys((prev) => [created, ...prev]);
    setSessionApiKey(created.key);
    writeStoredIntegrationKey({ keyId: created.key_id, secret: created.key });
    setShowKeyForm(false);
    setNewKey({ name: '', permissions: [API_KEY_PERMISSION_OPTIONS[0]] });

    const webhooksResult = await fetchApi<Webhook[]>('/api/v1/webhooks', {
      headers: { 'X-API-Key': created.key },
    });
    if (webhooksResult.success && webhooksResult.data) {
      setWebhooks(webhooksResult.data);
    } else {
      const detail =
        webhooksResult.error ||
        'Could not load webhooks. Your key was created; refresh the page or try again later.';
      addToast(detail, 'error');
      console.error('Failed to load webhooks after API key creation', webhooksResult);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    const result = await fetchApi(`/api/v1/api-keys/${keyId}`, {
      method: 'DELETE',
      headers: adminAuthHeaders(),
    });
    if (!result.success) {
      const detail =
        result.error ||
        result.message ||
        'Failed to revoke API key.';
      addToast(detail, 'error');
      return;
    }
    const stored = readStoredIntegrationKey();
    if (stored && stored.keyId === keyId) {
      clearStoredIntegrationKey();
      setSessionApiKey(null);
      setWebhooks([]);
    }
    setApiKeys((prev) => prev.filter((key) => key.key_id !== keyId));
  };

  const handleCopyKey = async (keyId: string) => {
    const secret = getFullSecretForKeyId(keyId);
    if (!secret) {
      addToast(
        'Cannot copy: listed keys are masked. The full secret is only shown once when you create a key. Generate a new key if you no longer have it saved.',
        'error',
      );
      return;
    }
    try {
      await navigator.clipboard.writeText(secret);
      setCopiedId(keyId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Clipboard write failed', err);
      addToast(
        err instanceof Error ? `Could not copy: ${err.message}` : 'Could not copy to clipboard',
        'error',
      );
    }
  };

  const handleCreateWebhook = async () => {
    if (!sessionApiKey) return;
    setWebhookError(null);
    try {
      const url = new URL(newWebhook.url);
      if (url.protocol !== 'https:') {
        setWebhookError('Webhook URL must use HTTPS');
        return;
      }
    } catch {
      setWebhookError('Invalid webhook URL');
      return;
    }
    const result = await fetchApi<Webhook>('/api/v1/webhooks', {
      method: 'POST',
      headers: {
        'X-API-Key': sessionApiKey,
      },
      body: JSON.stringify(newWebhook),
    });
    if (!result.success || !result.data) {
      setWebhookError(result.error || 'Failed to register webhook');
      return;
    }
    setWebhooks((prev) => [result.data!, ...prev]);
    setShowWebhookForm(false);
    setNewWebhook({ url: '', events: ['simulation_completed'] });
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    if (!sessionApiKey) return;
    const result = await fetchApi(`/api/v1/webhooks/${webhookId}`, {
      method: 'DELETE',
      headers: {
        'X-API-Key': sessionApiKey,
      },
    });
    if (!result.success) {
      const detail =
        result.error ||
        result.message ||
        'Failed to delete webhook.';
      addToast(detail, 'error');
      return;
    }
    setWebhooks((prev) => prev.filter((webhook) => webhook.webhook_id !== webhookId));
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

  const handleUnlockAdmin = () => {
    setAdminGateError(null);
    const v = adminInput.trim();
    if (!v) {
      setAdminGateError('Enter the admin key from the server ADMIN_API_KEY setting.');
      return;
    }
    setAdminApiKey(v);
    setAdminInput('');
    setAdminUnlocked(true);
  };

  if (!adminUnlocked) {
    return (
      <div className="space-y-6 animate-fade-in max-w-lg">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">API Key Management</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Enter the server admin key (same value as <code className="text-accent">ADMIN_API_KEY</code> in
            the backend <code className="text-slate-500">.env</code>). This unlocks listing and creating
            integration API keys. It is stored only in this browser tab (session storage).
          </p>
        </div>
        {adminGateError && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {adminGateError}
          </div>
        )}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-400">Admin key</label>
          <input
            type="password"
            autoComplete="off"
            value={adminInput}
            onChange={(e) => setAdminInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUnlockAdmin()}
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent"
            placeholder="Bearer value (paste secret only, not the word Bearer)"
          />
          <Button className="w-full sm:w-auto" onClick={handleUnlockAdmin}>
            Unlock
          </Button>
        </div>
      </div>
    );
  }

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
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            clearAdminApiKey();
            setAdminUnlocked(false);
            setApiKeys([]);
            setWebhooks([]);
            setPageError(null);
          }}
        >
          Sign out admin
        </Button>
      </div>

      {pageError && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {pageError}
        </div>
      )}

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
            {createKeyError && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {createKeyError}
              </div>
            )}
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
                  {API_KEY_PERMISSION_OPTIONS.map((permission) => (
                    <button
                      key={permission}
                      onClick={() => togglePermission(permission)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        newKey.permissions.includes(permission)
                          ? 'bg-accent text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {permission}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowKeyForm(false);
                    setCreateKeyError(null);
                  }}
                >
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
          {apiKeys.map((key) => {
            const copyableSecret = getFullSecretForKeyId(key.key_id);
            return (
            <div key={key.key_id} className="flex items-center justify-between p-4 bg-slate-700/20 rounded-lg">
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
                  type="button"
                  onClick={() => handleCopyKey(key.key_id)}
                  disabled={!copyableSecret}
                  className={`p-2 transition-colors ${
                    copyableSecret
                      ? 'text-slate-400 hover:text-slate-200'
                      : 'cursor-not-allowed text-slate-600 opacity-60'
                  }`}
                  title={
                    copyableSecret
                      ? 'Copy full API key'
                      : 'Full secret is only available once when the key is created (this tab). Generate a new key if you lost it.'
                  }
                >
                  {copiedId === key.key_id ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => handleRevokeKey(key.key_id)}
                  className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                  title="Revoke key"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            );
          })}
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
              disabled={!sessionApiKey}
            >
              Add Webhook
            </Button>
          </div>
        }
      >
        {!sessionApiKey && (
          <div className="mb-6 rounded-lg border border-slate-700 bg-slate-700/20 p-4 text-sm text-slate-400">
            Generate an API key to load webhooks and manage them. The secret is kept in this browser tab (session storage) until you revoke that key.
          </div>
        )}
        {/* Create Webhook Form */}
        {showWebhookForm && (
          <div className="mb-6 p-4 bg-slate-700/20 rounded-lg">
            <h3 className="font-medium text-slate-200 mb-4">Register New Webhook</h3>
            {webhookError && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {webhookError}
              </div>
            )}
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
                    placeholder="https://api.example.com/webhooks/scenariolab"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Events</label>
                <div className="flex flex-wrap gap-2">
                  {WEBHOOK_EVENT_OPTIONS.map((event) => (
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
                <Button size="sm" onClick={handleCreateWebhook} disabled={!sessionApiKey}>
                  Register
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Webhooks List */}
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.webhook_id} className="flex items-center justify-between p-4 bg-slate-700/20 rounded-lg">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  webhook.active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600/20 text-slate-400'
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
                  webhook.active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600/20 text-slate-400'
                }`}>
                  {webhook.active ? 'Active' : 'Inactive'}
                </span>
                <button
                  onClick={() => handleDeleteWebhook(webhook.webhook_id)}
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
