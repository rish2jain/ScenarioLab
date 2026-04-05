import { create } from 'zustand';
import type {
  Simulation,
  Playbook,
  Report,
  ChatMessage,
  AgentMessage,
  UploadedFile,
} from './types';

// Simulation Store
interface SimulationState {
  simulations: Simulation[];
  currentSimulation: Simulation | null;
  isLoading: boolean;
  error: string | null;
  agentMessages: AgentMessage[];
  setSimulations: (simulations: Simulation[]) => void;
  setCurrentSimulation: (simulation: Simulation | null) => void;
  addSimulation: (simulation: Simulation) => void;
  removeSimulation: (id: string) => void;
  updateSimulation: (id: string, updates: Partial<Simulation>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setAgentMessages: (messages: AgentMessage[]) => void;
  addAgentMessage: (message: AgentMessage) => void;
}

export const useSimulationStore = create<SimulationState>((set) => ({
  simulations: [],
  currentSimulation: null,
  isLoading: false,
  error: null,
  agentMessages: [],
  setSimulations: (simulations) => set({ simulations }),
  setCurrentSimulation: (simulation) => set({ currentSimulation: simulation }),
  addSimulation: (simulation) =>
    set((state) => ({
      simulations: [simulation, ...state.simulations],
    })),
  removeSimulation: (id) =>
    set((state) => ({
      simulations: state.simulations.filter((s) => s.id !== id),
      currentSimulation:
        state.currentSimulation?.id === id ? null : state.currentSimulation,
    })),
  updateSimulation: (id, updates) =>
    set((state) => ({
      simulations: state.simulations.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
      currentSimulation:
        state.currentSimulation?.id === id
          ? { ...state.currentSimulation, ...updates }
          : state.currentSimulation,
    })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setAgentMessages: (agentMessages) => set({ agentMessages }),
  addAgentMessage: (message) =>
    set((state) => ({
      agentMessages: [...state.agentMessages, message],
    })),
}));

// Playbook Store
interface PlaybookState {
  playbooks: Playbook[];
  selectedPlaybook: Playbook | null;
  isLoading: boolean;
  error: string | null;
  setPlaybooks: (playbooks: Playbook[]) => void;
  setSelectedPlaybook: (playbook: Playbook | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const usePlaybookStore = create<PlaybookState>((set) => ({
  playbooks: [],
  selectedPlaybook: null,
  isLoading: false,
  error: null,
  setPlaybooks: (playbooks) => set({ playbooks }),
  setSelectedPlaybook: (playbook) => set({ selectedPlaybook: playbook }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));

// Report Store
interface ReportState {
  reports: Report[];
  currentReport: Report | null;
  isLoading: boolean;
  error: string | null;
  setReports: (reports: Report[]) => void;
  setCurrentReport: (report: Report | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useReportStore = create<ReportState>((set) => ({
  reports: [],
  currentReport: null,
  isLoading: false,
  error: null,
  setReports: (reports) => set({ reports }),
  setCurrentReport: (report) => set({ currentReport: report }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));

// Chat Store
interface ChatState {
  messages: ChatMessage[];
  selectedAgentId: string | null;
  isLoading: boolean;
  error: string | null;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setSelectedAgentId: (agentId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  selectedAgentId: null,
  isLoading: false,
  error: null,
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),
  setSelectedAgentId: (agentId) => set({ selectedAgentId: agentId }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}));

// Upload Store
interface UploadState {
  files: UploadedFile[];
  isUploading: boolean;
  addFile: (file: UploadedFile) => void;
  updateFile: (id: string, updates: Partial<UploadedFile>) => void;
  removeFile: (id: string) => void;
  setIsUploading: (isUploading: boolean) => void;
  clearFiles: () => void;
  /** Merge persisted seeds from GET /api/seeds (API-first order, deduped by id). */
  mergeSeedsFromApi: (seeds: UploadedFile[]) => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  files: [],
  isUploading: false,
  addFile: (file) =>
    set((state) => ({
      files: [...state.files, file],
    })),
  updateFile: (id, updates) =>
    set((state) => ({
      files: state.files.map((f) =>
        f.id === id ? { ...f, ...updates } : f
      ),
    })),
  removeFile: (id) =>
    set((state) => ({
      files: state.files.filter((f) => f.id !== id),
    })),
  setIsUploading: (isUploading) => set({ isUploading }),
  clearFiles: () => set({ files: [] }),
  mergeSeedsFromApi: (seeds) =>
    set((state) => {
      const seen = new Set<string>();
      const merged: UploadedFile[] = [];
      for (const s of seeds) {
        if (s.id && !seen.has(s.id)) {
          seen.add(s.id);
          merged.push(s);
        }
      }
      for (const f of state.files) {
        if (!seen.has(f.id)) {
          seen.add(f.id);
          merged.push(f);
        }
      }
      return { files: merged };
    }),
}));
