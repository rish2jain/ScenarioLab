'use client';

import { useState, useCallback } from 'react';
import { FileText, Loader2, CheckCircle, AlertCircle, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DropZone } from '@/components/ui/DropZone';
import { useUploadStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function UploadPage() {
  const { files, addFile, updateFile, removeFile, setIsUploading, isUploading } = useUploadStore();
  const [isProcessing, setIsProcessing] = useState(false);

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
          // Upload file with progress
          await api.uploadFile(file, (progress) => {
            updateFile(fileId, { progress });
          });

          updateFile(fileId, { status: 'completed', progress: 100 });
        } catch (error) {
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

  const handleProcessSeeds = async () => {
    const completedFiles = files.filter((f) => f.status === 'completed');
    if (completedFiles.length === 0) return;

    setIsProcessing(true);

    // Update all files to processing
    completedFiles.forEach((file) => {
      updateFile(file.id, { status: 'processing' });
    });

    try {
      await api.processSeeds(completedFiles.map((f) => f.id));

      // Mark all as completed
      completedFiles.forEach((file) => {
        updateFile(file.id, { status: 'completed' });
      });
    } catch (error) {
      completedFiles.forEach((file) => {
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
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />;
      case 'uploading':
        return <Loader2 className="w-5 h-5 text-accent animate-spin" />;
      default:
        return null;
    }
  };

  const completedCount = files.filter((f) => f.status === 'completed').length;

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
        {completedCount > 0 && (
          <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
            <div>
              <p className="text-sm font-medium text-slate-200">
                {completedCount} file{completedCount !== 1 ? 's' : ''} ready to process
              </p>
              <p className="text-xs text-slate-400 mt-1">
                This will extract entities and build the knowledge graph
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
