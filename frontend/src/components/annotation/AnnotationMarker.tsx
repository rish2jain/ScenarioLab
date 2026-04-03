'use client';

import React, { useState } from 'react';
import { clsx } from 'clsx';
import { MessageSquarePlus, Check, X, AlertTriangle } from 'lucide-react';
import { useAnnotationStore, annotationTagConfig } from '@/lib/annotationStore';
import type { AnnotationTag } from '@/lib/types';

interface AnnotationMarkerProps {
  messageId: string;
  simulationId: string;
  roundNumber: number;
  annotator?: string;
  className?: string;
}

export function AnnotationMarker({
  messageId,
  simulationId,
  roundNumber,
  annotator = 'Consultant',
  className,
}: AnnotationMarkerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<AnnotationTag>('agree');
  const [note, setNote] = useState('');
  
  const { addAnnotation, getAnnotationCountForMessage, getAnnotationsForMessage } = useAnnotationStore();
  const annotationCount = getAnnotationCountForMessage(messageId);
  const annotations = getAnnotationsForMessage(messageId);

  const handleSubmit = () => {
    if (!note.trim()) return;
    
    addAnnotation({
      simulationId,
      messageId,
      roundNumber,
      tag: selectedTag,
      note: note.trim(),
      annotator,
    });
    
    setNote('');
    setIsOpen(false);
  };

  const handleCancel = () => {
    setNote('');
    setIsOpen(false);
  };

  // Get the dominant tag for the badge
  const getDominantTag = (): AnnotationTag | null => {
    if (annotations.length === 0) return null;
    const counts = annotations.reduce((acc, a) => {
      acc[a.tag] = (acc[a.tag] || 0) + 1;
      return acc;
    }, {} as Record<AnnotationTag, number>);
    return (Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] as AnnotationTag) || null;
  };

  const dominantTag = getDominantTag();

  return (
    <div className={clsx('relative', className)}>
      {/* Marker Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-all',
          annotationCount > 0
            ? 'bg-slate-700 text-slate-200 hover:bg-slate-600'
            : 'opacity-0 group-hover:opacity-100 bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
        )}
      >
        {dominantTag ? (
          <>
            {dominantTag === 'agree' && <Check className="w-3 h-3 text-green-400" />}
            {dominantTag === 'disagree' && <X className="w-3 h-3 text-red-400" />}
            {dominantTag === 'caveat' && <AlertTriangle className="w-3 h-3 text-amber-400" />}
            {annotationCount > 1 && (
              <span className="ml-1 bg-slate-600 text-slate-200 w-4 h-4 rounded-full flex items-center justify-center text-[10px]">
                {annotationCount}
              </span>
            )}
          </>
        ) : (
          <>
            <MessageSquarePlus className="w-3 h-3" />
            <span>Annotate</span>
          </>
        )}
      </button>

      {/* Annotation Form Popup */}
      {isOpen && (
        <div className="absolute z-50 mt-2 w-72 bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-3">
          <div className="space-y-3">
            {/* Tag Selection */}
            <div className="flex gap-2">
              {(Object.keys(annotationTagConfig) as AnnotationTag[]).map((tag) => {
                const config = annotationTagConfig[tag];
                return (
                  <button
                    key={tag}
                    onClick={() => setSelectedTag(tag)}
                    className={clsx(
                      'flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium transition-colors',
                      selectedTag === tag
                        ? 'text-white'
                        : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                    )}
                    style={{
                      backgroundColor: selectedTag === tag ? config.color : undefined,
                    }}
                  >
                    {tag === 'agree' && <Check className="w-3 h-3" />}
                    {tag === 'disagree' && <X className="w-3 h-3" />}
                    {tag === 'caveat' && <AlertTriangle className="w-3 h-3" />}
                    {config.label}
                  </button>
                );
              })}
            </div>

            {/* Note Input */}
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add your annotation..."
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 resize-none"
              rows={3}
              autoFocus
            />

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                className="flex-1 px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!note.trim()}
                className="flex-1 px-3 py-1.5 bg-accent text-white rounded-lg text-xs font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Add
              </button>
            </div>
          </div>

          {/* Existing Annotations */}
          {annotations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <div className="text-xs text-slate-500 mb-2">Previous annotations</div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {annotations.map((annotation) => {
                  const config = annotationTagConfig[annotation.tag];
                  return (
                    <div
                      key={annotation.id}
                      className="p-2 bg-slate-700/50 rounded text-xs"
                    >
                      <div className="flex items-center gap-1.5 mb-1">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: config.color }}
                        />
                        <span style={{ color: config.color }}>{config.label}</span>
                        <span className="text-slate-500 ml-auto">
                          {new Date(annotation.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-slate-300">{annotation.note}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AnnotationMarker;
