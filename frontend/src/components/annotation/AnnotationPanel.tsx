'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { clsx } from 'clsx';
import { X, Filter, Check, AlertTriangle, MessageSquare, Trash2 } from 'lucide-react';
import { useAnnotationStore, annotationTagConfig } from '@/lib/annotationStore';
import type { AnnotationTag, Annotation } from '@/lib/types';

interface AnnotationPanelProps {
  simulationId: string;
  className?: string;
  onClose?: () => void;
}

type SortOption = 'round' | 'tag' | 'timestamp';

export function AnnotationPanel({
  simulationId,
  className,
  onClose,
}: AnnotationPanelProps) {
  const [filterTag, setFilterTag] = useState<AnnotationTag | 'all'>('all');
  const [filterAnnotator, setFilterAnnotator] = useState<string>('all');
  const [filterRound, setFilterRound] = useState<number | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortOption>('timestamp');

  const {
    getAllAnnotations,
    removeAnnotation,
    loadAnnotations,
    isLoading,
  } = useAnnotationStore();

  // Load annotations from backend on mount
  useEffect(() => {
    loadAnnotations(simulationId);
  }, [simulationId, loadAnnotations]);

  // Get all annotations for this simulation
  const allAnnotations = getAllAnnotations().filter(
    (a) => a.simulationId === simulationId
  );

  // Get unique annotators and rounds for filter options
  const annotators = useMemo(() => {
    return Array.from(new Set(allAnnotations.map((a) => a.annotator)));
  }, [allAnnotations]);

  const rounds = useMemo(() => {
    return Array.from(new Set(allAnnotations.map((a) => a.roundNumber))).sort((a, b) => a - b);
  }, [allAnnotations]);

  // Filter and sort annotations
  const filteredAnnotations = useMemo(() => {
    let filtered = allAnnotations;

    if (filterTag !== 'all') {
      filtered = filtered.filter((a) => a.tag === filterTag);
    }

    if (filterAnnotator !== 'all') {
      filtered = filtered.filter((a) => a.annotator === filterAnnotator);
    }

    if (filterRound !== 'all') {
      filtered = filtered.filter((a) => a.roundNumber === filterRound);
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'round':
          return a.roundNumber - b.roundNumber;
        case 'tag':
          return a.tag.localeCompare(b.tag);
        case 'timestamp':
        default:
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      }
    });

    return filtered;
  }, [allAnnotations, filterTag, filterAnnotator, filterRound, sortBy]);

  // Group annotations by round for display
  const groupedByRound = useMemo(() => {
    return filteredAnnotations.reduce((acc, annotation) => {
      if (!acc[annotation.roundNumber]) {
        acc[annotation.roundNumber] = [];
      }
      acc[annotation.roundNumber].push(annotation);
      return acc;
    }, {} as Record<number, Annotation[]>);
  }, [filteredAnnotations]);

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this annotation?')) {
      removeAnnotation(id);
    }
  };

  const getTagIcon = (tag: AnnotationTag) => {
    switch (tag) {
      case 'agree':
        return <Check className="w-3 h-3" />;
      case 'disagree':
        return <X className="w-3 h-3" />;
      case 'caveat':
        return <AlertTriangle className="w-3 h-3" />;
    }
  };

  return (
    <div className={clsx('flex flex-col h-full bg-slate-800/50 border-l border-slate-700', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-accent" />
          <h2 className="font-semibold text-slate-200">Annotations</h2>
          <span className="px-2 py-0.5 bg-slate-700 rounded-full text-xs text-slate-300">
            {allAnnotations.length}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-slate-700 space-y-3">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Filter className="w-4 h-4" />
          <span>Filters</span>
        </div>

        {/* Tag Filter */}
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setFilterTag('all')}
            className={clsx(
              'px-2 py-1 rounded text-xs font-medium transition-colors',
              filterTag === 'all'
                ? 'bg-slate-600 text-white'
                : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
            )}
          >
            All
          </button>
          {(Object.keys(annotationTagConfig) as AnnotationTag[]).map((tag) => {
            const config = annotationTagConfig[tag];
            return (
              <button
                key={tag}
                onClick={() => setFilterTag(tag)}
                className={clsx(
                  'px-2 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1',
                  filterTag === tag
                    ? 'text-white'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                )}
                style={{
                  backgroundColor: filterTag === tag ? config.color : undefined,
                }}
              >
                {getTagIcon(tag)}
                {config.label}
              </button>
            );
          })}
        </div>

        {/* Annotator Filter */}
        {annotators.length > 0 && (
          <select
            value={filterAnnotator}
            onChange={(e) => setFilterAnnotator(e.target.value)}
            className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50"
          >
            <option value="all">All Annotators</option>
            {annotators.map((annotator) => (
              <option key={annotator} value={annotator}>
                {annotator}
              </option>
            ))}
          </select>
        )}

        {/* Round Filter */}
        {rounds.length > 0 && (
          <select
            value={filterRound}
            onChange={(e) => setFilterRound(e.target.value === 'all' ? 'all' : Number(e.target.value))}
            className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50"
          >
            <option value="all">All Rounds</option>
            {rounds.map((round) => (
              <option key={round} value={round}>
                Round {round}
              </option>
            ))}
          </select>
        )}

        {/* Sort */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none"
          >
            <option value="timestamp">Time</option>
            <option value="round">Round</option>
            <option value="tag">Tag</option>
          </select>
        </div>
      </div>

      {/* Annotations List */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredAnnotations.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No annotations yet</p>
            <p className="text-xs mt-1">Add annotations to messages in the simulation feed</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedByRound)
              .sort(([a], [b]) => Number(b) - Number(a))
              .map(([round, annotations]) => (
                <div key={round}>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-2 py-0.5 bg-slate-700 rounded text-xs font-medium text-slate-300">
                      Round {round}
                    </span>
                    <div className="flex-1 h-px bg-slate-700" />
                    <span className="text-xs text-slate-500">
                      {annotations.length} annotation{annotations.length !== 1 ? 's' : ''}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {annotations.map((annotation) => {
                      const config = annotationTagConfig[annotation.tag];
                      return (
                        <div
                          key={annotation.id}
                          className="p-3 bg-slate-700/30 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors group"
                        >
                          <div className="flex items-start gap-2">
                            <div
                              className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
                              style={{
                                backgroundColor: config.bgColor,
                                color: config.color,
                              }}
                            >
                              {getTagIcon(annotation.tag)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span
                                  className="text-xs font-medium"
                                  style={{ color: config.color }}
                                >
                                  {config.label}
                                </span>
                                <span className="text-xs text-slate-500">
                                  by {annotation.annotator}
                                </span>
                                <span className="text-xs text-slate-600">
                                  {new Date(annotation.createdAt).toLocaleDateString()}
                                </span>
                              </div>
                              <p className="text-sm text-slate-300">{annotation.note}</p>
                            </div>
                            <button
                              onClick={() => handleDelete(annotation.id)}
                              className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-500 hover:text-red-400 hover:bg-slate-700 transition-all"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {allAnnotations.length > 0 && (
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total: {allAnnotations.length}</span>
            <div className="flex gap-3">
              {(Object.keys(annotationTagConfig) as AnnotationTag[]).map((tag) => {
                const count = allAnnotations.filter((a) => a.tag === tag).length;
                if (count === 0) return null;
                const config = annotationTagConfig[tag];
                return (
                  <span key={tag} className="flex items-center gap-1">
                    <span style={{ color: config.color }}>{config.label}:</span>
                    <span>{count}</span>
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AnnotationPanel;
