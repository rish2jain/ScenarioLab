'use client';

import Link from 'next/link';
import { FileText } from 'lucide-react';
import { DropZone } from '@/components/ui/DropZone';
import type { UploadedFile } from '@/lib/types';

export interface SeedDocumentsProps {
  uploadedFiles: UploadedFile[];
  selectedSeedIds: string[];
  toggleSeedId: (id: string) => void;
  handleFilesDrop: (files: File[]) => Promise<void>;
}

export function SeedDocuments({
  uploadedFiles,
  selectedSeedIds,
  toggleSeedId,
  handleFilesDrop,
}: SeedDocumentsProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Seed Documents</h2>
        <p className="text-foreground-muted mt-1">
          Attach documents that agents will reference during the simulation
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground-muted">
            Previously Uploaded Files
          </h3>
          {uploadedFiles.some((f) => f.status === 'processing') && (
            <p className="text-xs text-foreground-muted">
              If graph extraction stays on &quot;processing&quot;,{' '}
              <Link href="/upload" className="text-accent underline hover:no-underline">
                Upload
              </Link>{' '}
              → Process Seeds re-queues extraction.
            </p>
          )}
          {uploadedFiles.map((file) => {
            const canSelect =
              file.status === 'completed' || file.status === 'processing';
            return (
              <label
                key={file.id}
                className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                  !canSelect
                    ? 'border-border bg-background-secondary/30 cursor-not-allowed opacity-70'
                    : selectedSeedIds.includes(file.id)
                      ? 'border-accent bg-accent/10 cursor-pointer'
                      : 'border-border bg-background-secondary/50 hover:border-border-hover cursor-pointer'
                }`}
              >
                <input
                  type="checkbox"
                  disabled={!canSelect}
                  checked={selectedSeedIds.includes(file.id)}
                  onChange={() => canSelect && toggleSeedId(file.id)}
                  className="w-4 h-4 rounded border-border-hover text-accent focus:ring-accent disabled:opacity-50"
                />
                <FileText className="w-5 h-5 text-foreground-muted flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                  <p className="text-xs text-foreground-muted">
                    {file.size < 1024 * 1024
                      ? (file.size / 1024).toFixed(1) + ' KB'
                      : (file.size / (1024 * 1024)).toFixed(1) + ' MB'}
                  </p>
                </div>
              </label>
            );
          })}
        </div>
      )}

      <div>
        <h3 className="text-sm font-medium text-foreground-muted mb-2">Upload New Files</h3>
        <DropZone onFilesDrop={handleFilesDrop} />
      </div>

      <div className="p-4 bg-background-secondary/30 rounded-lg border border-border">
        <div className="flex items-center justify-between">
          <span className="text-foreground-muted">Selected Documents</span>
          <span className="text-xl font-semibold text-foreground">
            {selectedSeedIds.length}
          </span>
        </div>
      </div>
    </div>
  );
}
