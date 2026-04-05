import { create } from 'zustand';
import type { Annotation, AnnotationTag, AnnotationFilter } from './types';
import { api } from './api';

interface AnnotationState {
  annotations: Record<string, Annotation[]>; // messageId -> annotations
  loadedSimulations: Set<string>; // Track which simulations have been loaded
  isLoading: boolean;
  addAnnotation: (annotation: Omit<Annotation, 'id' | 'createdAt'>) => Promise<void>;
  loadAnnotations: (simulationId: string) => Promise<void>;
  getAnnotationsForMessage: (messageId: string) => Annotation[];
  getAnnotationsByFilter: (filter: AnnotationFilter) => Annotation[];
  removeAnnotation: (id: string) => Promise<void>;
  getAnnotationCountForMessage: (messageId: string) => number;
  getAllAnnotations: () => Annotation[];
}

// Generate unique ID for local fallback
const generateId = () => `anno-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

export const useAnnotationStore = create<AnnotationState>((set, get) => ({
  annotations: {},
  loadedSimulations: new Set<string>(),
  isLoading: false,

  loadAnnotations: async (simulationId: string) => {
    // Skip if already loaded
    if (get().loadedSimulations.has(simulationId)) {
      return;
    }

    set({ isLoading: true });

    try {
      const annotations = await api.getAnnotations(simulationId);

      set((state) => {
        const newAnnotations = { ...state.annotations };

        // Group annotations by message_id
        for (const annotation of annotations) {
          const key = annotation.messageId || 'general';
          if (!newAnnotations[key]) {
            newAnnotations[key] = [];
          }
          // Avoid duplicates
          if (!newAnnotations[key].some(a => a.id === annotation.id)) {
            newAnnotations[key].push(annotation);
          }
        }

        return {
          annotations: newAnnotations,
          loadedSimulations: new Set(state.loadedSimulations).add(simulationId),
          isLoading: false,
        };
      });
    } catch (error) {
      console.error('Failed to load annotations:', error);
      set({ isLoading: false });
    }
  },

  addAnnotation: async (annotationData) => {
    // Create local annotation immediately for optimistic UI
    const localId = generateId();
    const localAnnotation: Annotation = {
      ...annotationData,
      id: localId,
      createdAt: new Date().toISOString(),
    };

    // Add to local state optimistically
    set((state) => {
      const messageAnnotations = state.annotations[annotationData.messageId] || [];
      return {
        annotations: {
          ...state.annotations,
          [annotationData.messageId]: [...messageAnnotations, localAnnotation],
        },
      };
    });

    // Try to save to backend
    try {
      const createdAnnotation = await api.createAnnotation({
        simulationId: annotationData.simulationId,
        messageId: annotationData.messageId,
        roundNumber: annotationData.roundNumber,
        tag: annotationData.tag,
        note: annotationData.note,
        annotator: annotationData.annotator,
      } as Omit<Annotation, 'id' | 'createdAt'>);

      if (createdAnnotation) {
        // Replace local annotation with server annotation
        set((state) => {
          const messageAnnotations = state.annotations[annotationData.messageId] || [];
          return {
            annotations: {
              ...state.annotations,
              [annotationData.messageId]: messageAnnotations.map(a =>
                a.id === localId ? createdAnnotation : a
              ),
            },
          };
        });
      }
    } catch (error) {
      console.error('Failed to save annotation to backend:', error);
      // Keep local annotation on error
    }
  },

  getAnnotationsForMessage: (messageId: string) => {
    return get().annotations[messageId] || [];
  },

  getAnnotationsByFilter: (filter: AnnotationFilter) => {
    const allAnnotations = get().getAllAnnotations();
    return allAnnotations.filter((annotation) => {
      if (filter.tag && annotation.tag !== filter.tag) return false;
      if (filter.annotator && annotation.annotator !== filter.annotator) return false;
      if (filter.round !== undefined && annotation.roundNumber !== filter.round) return false;
      return true;
    });
  },

  removeAnnotation: async (id: string) => {
    // Remove optimistically
    set((state) => {
      const newAnnotations: Record<string, Annotation[]> = {};
      Object.entries(state.annotations).forEach(([mid, annotations]) => {
        const filtered = annotations.filter((a) => a.id !== id);
        if (filtered.length > 0) {
          newAnnotations[mid] = filtered;
        }
      });
      return { annotations: newAnnotations };
    });

    // Try to delete from backend
    try {
      await api.deleteAnnotation(id);
    } catch (error) {
      console.error('Failed to delete annotation from backend:', error);
      // On error, the annotation is already removed locally
      // Could add it back if needed, but for now just log
    }
  },

  getAnnotationCountForMessage: (messageId: string) => {
    return (get().annotations[messageId] || []).length;
  },

  getAllAnnotations: () => {
    return Object.values(get().annotations).flat();
  },
}));

// Tag configuration for UI
export const annotationTagConfig: Record<AnnotationTag, { label: string; color: string; bgColor: string; icon: string }> = {
  agree: {
    label: 'Agree',
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.2)',
    icon: 'Check',
  },
  disagree: {
    label: 'Disagree',
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.2)',
    icon: 'X',
  },
  caveat: {
    label: 'Caveat',
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.2)',
    icon: 'AlertTriangle',
  },
};
