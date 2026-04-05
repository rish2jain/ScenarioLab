'use client';

import { useCallback, useMemo, useState } from 'react';
import { clsx } from 'clsx';
import { Upload, File, X } from 'lucide-react';

/** Parse a comma-separated HTML accept string into display tokens (extensions or MIME shortcuts). */
function displayTokensFromAccept(accept: string): string[] {
  return accept
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((t) => (t.startsWith('.') ? t.toLowerCase() : t));
}

interface DropZoneProps {
  onFilesDrop: (files: File[]) => void;
  accept?: string;
  maxFiles?: number;
  maxSize?: number; // in bytes
  className?: string;
}

export function DropZone({
  onFilesDrop,
  accept = '.md,.txt,.pdf,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.gif,.webp,.bmp',
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024, // 50MB
  className,
}: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const acceptDisplayTokens = useMemo(() => displayTokensFromAccept(accept), [accept]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const files = Array.from(e.dataTransfer.files);
      const validFiles = files.filter(
        (file) => file.size <= maxSize
      ).slice(0, maxFiles);

      if (validFiles.length > 0) {
        onFilesDrop(validFiles);
      }
    },
    [onFilesDrop, maxFiles, maxSize]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      const validFiles = files.filter(
        (file) => file.size <= maxSize
      ).slice(0, maxFiles);

      if (validFiles.length > 0) {
        onFilesDrop(validFiles);
      }
    },
    [onFilesDrop, maxFiles, maxSize]
  );

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={clsx(
        'relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200',
        isDragOver
          ? 'border-accent bg-accent/10'
          : 'border-slate-600 hover:border-slate-500 bg-slate-800/30',
        className
      )}
    >
      <input
        type="file"
        multiple
        accept={accept}
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />
      <div className="flex flex-col items-center gap-3">
        <div
          className={clsx(
            'w-16 h-16 rounded-full flex items-center justify-center transition-colors',
            isDragOver ? 'bg-accent/20' : 'bg-slate-700'
          )}
        >
          <Upload
            className={clsx(
              'w-8 h-8 transition-colors',
              isDragOver ? 'text-accent' : 'text-slate-400'
            )}
          />
        </div>
        <div>
          <p className="text-slate-200 font-medium">
            Drop seed materials here
          </p>
          <p className="text-slate-400 text-sm mt-1">
            or click to browse files
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {acceptDisplayTokens.map((ext) => (
            <span
              key={ext}
              className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300"
            >
              {ext}
            </span>
          ))}
        </div>
        <p className="text-slate-500 text-xs">
          Max file size: {(maxSize / 1024 / 1024).toFixed(0)}MB
        </p>
      </div>
    </div>
  );
}

interface FileListProps {
  files: Array<{
    id: string;
    name: string;
    size: number;
    progress: number;
    status: string;
  }>;
  onRemove: (id: string) => void;
}

export function FileList({ files, onRemove }: FileListProps) {
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (files.length === 0) return null;

  return (
    <div className="space-y-2 mt-4">
      {files.map((file) => (
        <div
          key={file.id}
          className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg border border-slate-700"
        >
          <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0">
            <File className="w-5 h-5 text-slate-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">
              {file.name}
            </p>
            <p className="text-xs text-slate-400">{formatSize(file.size)}</p>
            {file.status === 'uploading' && (
              <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent transition-all duration-300"
                  style={{ width: `${file.progress}%` }}
                />
              </div>
            )}
          </div>
          <button
            onClick={() => onRemove(file.id)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
