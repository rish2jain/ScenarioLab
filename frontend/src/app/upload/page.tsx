'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { FileText, Loader2, CheckCircle, AlertCircle, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DropZone } from '@/components/ui/DropZone';
import { useUploadStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { UploadedFile } from '@/lib/types';

/** Client-only placeholder ids from the drop handler; never sent to /api/seeds/process. */
function isPersistedSeedId(id: string): boolean {
  return id.length > 0 && !id.startsWith('file-');
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

export default function UploadPage() {
  const { files, addFile, updateFile, removeFile, setIsUploading, mergeSeedsFromApi } =
    useUploadStore();
  const [isProcessing, setIsProcessing] = useState(false);

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

  const handleFilesDrop = useCallback(
    async (newFiles: File[]) => {
      for (const file of newFiles) {
        const fileId = `file-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
        
        // Add file to store
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

        try {
          const uploaded = await api.uploadFile(file, (progress) => {
            updateFile(fileId, { progress });
          });

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
        } catch {
          updateFile(fileId, {
            status: 'error',
            errorMessage: 'Upload failed',
          });
        }
      }

      setIsUploading(false);
    },
    [addFile, updateFile, setIsUploading]
  );

  const processableFiles = useMemo(
    () => files.filter(isProcessableFile),
    [files]
  );

  const handleProcessSeeds = async () => {
    // Include `processing` so stuck seeds (lost background task / restart) can hit
    // POST /api/seeds/process, which re-queues entity extraction per graph router.
    if (isProcessing) return;
    if (processableFiles.length === 0) return;

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
            ui === 'error'
              ? row.error_message ?? 'Graph extraction failed'
              : undefined,
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

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
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

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Upload Seed Materials</h1>
        <p className="text-slate-400 mt-1 text-sm sm:text-base">
          Import strategic documents to build your knowledge graph
        </p>
      </div>

      {/* Upload Area */}
      <Card padding="md" className="md:padding-lg">
        <DropZone onFilesDrop={handleFilesDrop} />

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-sm font-medium text-slate-300">
              Uploaded Files ({files.length})
            </h3>
            <div className="space-y-2">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg border border-slate-700"
                >
                  <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {formatSize(file.size)}
                    </p>
                    {file.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent transition-all duration-300"
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(file.status)}
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
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
          <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
            <div>
              <p className="text-sm font-medium text-slate-200">
                {processableCount} file{processableCount !== 1 ? 's' : ''} ready to process
                {(files.some((f) => f.status === 'error') ||
                  files.some((f) => f.status === 'processing')) && (
                  <span className="text-slate-400 font-normal">
                    {' '}
                    (retries or re-queue stuck processing)
                  </span>
                )}
              </p>
              <p className="text-xs text-slate-400 mt-1">
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
              <h4 className="font-medium text-slate-200">Supported Formats</h4>
              <p className="text-sm text-slate-400 mt-1">
                Markdown, Text, PDF, and Word documents
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
              <h4 className="font-medium text-slate-200">What Happens Next</h4>
              <p className="text-sm text-slate-400 mt-1">
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
              <h4 className="font-medium text-slate-200">Privacy Note</h4>
              <p className="text-sm text-slate-400 mt-1">
                Documents are processed locally and stored securely
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
