'use client';

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import {
  FileText,
  Loader2,
  CheckCircle,
  AlertCircle,
  X,
  Trash2,
  Image,
  Table2,
  Presentation,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DropZone } from '@/components/ui/DropZone';
import { useToast } from '@/components/ui/Toast';
import { useUploadStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { UploadedFile } from '@/lib/types';

/** Client-only placeholder ids from the drop handler; never sent to /api/seeds/process. */
function isPersistedSeedId(id: string): boolean {
  return (
    id.length > 0 &&
    !id.startsWith('file-') &&
    !id.startsWith('local-seed-')
  );
}

function seedStatusToUiStatus(status: string): UploadedFile['status'] {
  if (status === 'processed') return 'completed';
  if (status === 'failed') return 'error';
  if (status === 'processing') return 'processing';
  return 'processing';
}

/** Seeds that can be sent to POST /api/seeds/process (persisted id + terminal/stuck UI status). */
function isProcessableFile(f: UploadedFile): boolean {
  return (
    (f.status === 'completed' ||
      f.status === 'error' ||
      f.status === 'processing') &&
    isPersistedSeedId(f.id)
  );
}

/** Return a file-type icon based on name/type. */
function getFileIcon(name: string) {
  const lower = name.toLowerCase();
  if (lower.endsWith('.pptx'))
    return <Presentation className="w-5 h-5 text-foreground-muted" />;
  if (lower.endsWith('.xlsx'))
    return <Table2 className="w-5 h-5 text-foreground-muted" />;
  if (/\.(png|jpe?g|gif|webp|bmp|svg)$/.test(lower))
    return <Image className="w-5 h-5 text-foreground-muted" />;
  return <FileText className="w-5 h-5 text-foreground-muted" />;
}

export default function UploadPage() {
  const { files, addFile, updateFile, removeFile, setIsUploading, mergeSeedsFromApi } =
    useUploadStore();
  const { addToast } = useToast();
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const uploadAbortByClientIdRef = useRef(new Map<string, AbortController>());
  const uploadCancelledClientIdsRef = useRef(new Set<string>());

  const cancelInFlightClientUpload = useCallback((clientId: string) => {
    uploadCancelledClientIdsRef.current.add(clientId);
    const ac = uploadAbortByClientIdRef.current.get(clientId);
    if (ac) {
      ac.abort();
      uploadAbortByClientIdRef.current.delete(clientId);
    }
    void api.cancelUploadByClientId(clientId).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const seeds = await api.listSeeds();
        if (!cancelled && seeds.length > 0) mergeSeedsFromApi(seeds);
      } catch {
        /* offline */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mergeSeedsFromApi]);

  // --- Selection ---
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
      prev.size === files.length ? new Set() : new Set(files.map((f) => f.id)),
    );
  }, [files]);

  // Clear selection when files change (e.g. after delete)
  useEffect(() => {
    setSelectedIds((prev) => {
      const validIds = new Set(files.map((f) => f.id));
      const filtered = new Set([...prev].filter((id) => validIds.has(id)));
      return filtered.size === prev.size ? prev : filtered;
    });
  }, [files]);

  // --- Bulk delete ---
  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setIsBulkDeleting(true);

    // Split into persisted (server) and client-only
    const serverIds = [...selectedIds].filter(isPersistedSeedId);
    const clientOnlyIds = [...selectedIds].filter((id) => !isPersistedSeedId(id));

    for (const id of clientOnlyIds) {
      cancelInFlightClientUpload(id);
      removeFile(id);
    }

    if (serverIds.length > 0) {
      try {
        const result = await api.deleteSeeds(serverIds);
        for (const id of result.deleted) {
          removeFile(id);
        }
        if (result.not_found.length > 0) {
          // Remove from UI anyway — they're gone from the server
          for (const id of result.not_found) {
            removeFile(id);
          }
        }
        if (result.graph_cleanup_failed.length > 0) {
          addToast(
            `${result.graph_cleanup_failed.length} file(s) could not be deleted because the graph database cleanup failed. Try again later.`,
            'error',
          );
        }
        const removedCount =
          result.deleted.length + result.not_found.length + clientOnlyIds.length;
        if (removedCount > 0 && result.graph_cleanup_failed.length === 0) {
          addToast(
            `Deleted ${removedCount} file${removedCount !== 1 ? 's' : ''}`,
            'success',
          );
        } else if (removedCount > 0) {
          addToast(
            `Removed ${removedCount} file${removedCount !== 1 ? 's' : ''}; some deletions need retry.`,
            'info',
          );
        }
      } catch {
        addToast('Failed to delete some files', 'error');
      }
    } else if (clientOnlyIds.length > 0) {
      addToast(
        `Removed ${clientOnlyIds.length} file${clientOnlyIds.length !== 1 ? 's' : ''}`,
        'success',
      );
    }

    setSelectedIds(new Set());
    setIsBulkDeleting(false);
  }, [selectedIds, removeFile, addToast, cancelInFlightClientUpload]);

  // --- Single delete ---
  const handleSingleDelete = useCallback(
    async (id: string) => {
      if (!isPersistedSeedId(id)) {
        cancelInFlightClientUpload(id);
        removeFile(id);
        return;
      }
      try {
        await api.deleteSeed(id);
      } catch {
        addToast('Failed to delete file from server', 'error');
        return;
      }
      removeFile(id);
    },
    [removeFile, addToast, cancelInFlightClientUpload],
  );

  // --- Upload ---
  const handleFilesDrop = useCallback(
    async (newFiles: File[]) => {
      for (const file of newFiles) {
        const fileId = `file-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

        addFile({
          id: fileId,
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'uploading',
          progress: 0,
          uploadedAt: new Date().toISOString(),
        });

        setIsUploading(true);

        const ac = new AbortController();
        uploadAbortByClientIdRef.current.set(fileId, ac);

        try {
          const uploaded = await api.uploadFile(file, {
            onProgress: (progress) => {
              updateFile(fileId, { progress });
            },
            signal: ac.signal,
            clientUploadId: fileId,
          });

          uploadAbortByClientIdRef.current.delete(fileId);

          if (uploadCancelledClientIdsRef.current.has(fileId)) {
            uploadCancelledClientIdsRef.current.delete(fileId);
            try {
              await api.deleteSeed(uploaded.id);
            } catch {
              /* best-effort: remove orphan if server committed after user cancelled */
            }
            continue;
          }

          const existing = useUploadStore.getState().files.find((f) => f.id === fileId);
          updateFile(fileId, {
            id: uploaded.id,
            name: uploaded.name,
            size: uploaded.size,
            type: uploaded.type,
            status: uploaded.status,
            progress: uploaded.progress,
            uploadedAt: existing?.uploadedAt ?? uploaded.uploadedAt,
            errorMessage: uploaded.errorMessage,
          });
        } catch (e) {
          uploadAbortByClientIdRef.current.delete(fileId);
          const aborted =
            (e instanceof DOMException && e.name === 'AbortError') ||
            (e instanceof Error && e.name === 'AbortError');
          if (aborted || uploadCancelledClientIdsRef.current.has(fileId)) {
            uploadCancelledClientIdsRef.current.delete(fileId);
            void api.cancelUploadByClientId(fileId).catch(() => {});
            continue;
          }
          updateFile(fileId, {
            status: 'error',
            errorMessage: 'Upload failed',
          });
        }
      }

      setIsUploading(false);
    },
    [addFile, updateFile, setIsUploading],
  );

  // --- Process seeds ---
  const processableFiles = useMemo(() => files.filter(isProcessableFile), [files]);

  const handleProcessSeeds = async () => {
    if (isProcessing || processableFiles.length === 0) return;
    setIsProcessing(true);

    try {
      const data = await api.processSeeds(processableFiles.map((f) => f.id));
      const processed = data.processed ?? [];
      const requeued = data.requeued ?? [];
      const notFound = data.not_found ?? [];

      for (const row of [...processed, ...requeued]) {
        const ui = seedStatusToUiStatus(row.status);
        updateFile(row.id, {
          status: ui,
          progress: ui === 'completed' ? 100 : ui === 'error' ? 0 : 90,
          errorMessage:
            ui === 'error' ? row.error_message ?? 'Graph extraction failed' : undefined,
        });
      }

      for (const id of notFound) {
        updateFile(id, {
          status: 'error',
          errorMessage: 'Seed not found on server. Re-upload the document.',
          progress: 0,
        });
      }
    } catch {
      processableFiles.forEach((file) => {
        updateFile(file.id, {
          status: 'error',
          errorMessage: 'Processing failed',
        });
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // --- Helpers ---
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span
            data-testid="upload-success-indicator"
            role="img"
            aria-label="Upload complete"
            className="inline-flex"
          >
            <CheckCircle className="w-5 h-5 text-green-400" aria-hidden="true" />
          </span>
        );
      case 'error':
        return (
          <span
            data-testid="upload-error-indicator"
            role="img"
            aria-label="Upload error"
            className="inline-flex"
          >
            <AlertCircle className="w-5 h-5 text-red-400" aria-hidden="true" />
          </span>
        );
      case 'processing':
        return <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />;
      case 'uploading':
        return <Loader2 className="w-5 h-5 text-accent animate-spin" />;
      default:
        return null;
    }
  };

  const processableCount = processableFiles.length;
  const selectionCount = selectedIds.size;
  const allSelected = files.length > 0 && selectionCount === files.length;

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Upload Seed Materials</h1>
        <p className="text-foreground-muted mt-1 text-sm sm:text-base">
          Import strategic documents to build your knowledge graph
        </p>
      </div>

      {/* Upload Area */}
      <Card padding="md" className="md:padding-lg">
        <DropZone onFilesDrop={handleFilesDrop} />

        {/* Selection toolbar */}
        {files.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer text-sm text-foreground-muted">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                    className="rounded border-border text-accent focus:ring-accent"
                  />
                  {allSelected ? 'Deselect all' : 'Select all'}
                </label>
                <h3 className="text-sm font-medium text-foreground-muted">
                  {files.length} file{files.length !== 1 ? 's' : ''}
                  {selectionCount > 0 && (
                    <span className="text-accent ml-1">
                      ({selectionCount} selected)
                    </span>
                  )}
                </h3>
              </div>
              {selectionCount > 0 && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleBulkDelete}
                  isLoading={isBulkDeleting}
                  leftIcon={!isBulkDeleting ? <Trash2 className="w-4 h-4" /> : undefined}
                >
                  Delete {selectionCount}
                </Button>
              )}
            </div>

            {/* File List */}
            <div className="space-y-2">
              {files.map((file) => (
                <div
                  key={file.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                    selectedIds.has(file.id)
                      ? 'bg-accent/5 border-accent/30'
                      : 'bg-background-secondary border-border'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(file.id)}
                    onChange={() => toggleSelect(file.id)}
                    className="rounded border-border text-accent focus:ring-accent flex-shrink-0"
                    aria-label={`Select ${file.name}`}
                  />
                  <div className="w-10 h-10 rounded-lg bg-background-tertiary flex items-center justify-center flex-shrink-0">
                    {getFileIcon(file.name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                    <p className="text-xs text-foreground-muted">{formatSize(file.size)}</p>
                    {file.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent transition-all duration-300"
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {file.errorMessage && (
                      <p className="text-xs text-red-400 mt-1">{file.errorMessage}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(file.status)}
                    <button
                      onClick={() => handleSingleDelete(file.id)}
                      className="p-1.5 rounded-lg text-foreground-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      aria-label={`Remove ${file.name}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Process Button */}
        {processableCount > 0 && (
          <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-background-secondary/50 rounded-lg border border-border">
            <div>
              <p className="text-sm font-medium text-foreground">
                {processableCount} file{processableCount !== 1 ? 's' : ''} ready to process
                {(files.some((f) => f.status === 'error') ||
                  files.some((f) => f.status === 'processing')) && (
                  <span className="text-foreground-muted font-normal">
                    {' '}
                    (retries or re-queue stuck processing)
                  </span>
                )}
              </p>
              <p className="text-xs text-foreground-muted mt-1">
                Extracts entities and builds the graph; use again if a file stays stuck
                on &quot;processing&quot; after upload or a server restart.
              </p>
            </div>
            <Button
              onClick={handleProcessSeeds}
              isLoading={isProcessing}
              leftIcon={!isProcessing ? <CheckCircle className="w-4 h-4" /> : undefined}
              className="w-full sm:w-auto"
            >
              Process Seeds
            </Button>
          </div>
        )}
      </Card>

      {/* Info Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h4 className="font-medium text-foreground">Supported Formats</h4>
              <p className="text-sm text-foreground-muted mt-1">
                Markdown, Text, PDF, Word, PowerPoint, Excel, and Images
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-4 h-4 text-green-400" />
            </div>
            <div>
              <h4 className="font-medium text-foreground">What Happens Next</h4>
              <p className="text-sm text-foreground-muted mt-1">
                Documents are parsed and entities are extracted for the knowledge graph
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h4 className="font-medium text-foreground">Privacy Note</h4>
              <p className="text-sm text-foreground-muted mt-1">
                Documents are processed locally and stored securely
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
