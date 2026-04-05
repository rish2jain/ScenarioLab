// Common / shared types

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  uploadedAt: string;
  errorMessage?: string;
}

export interface DashboardStats {
  totalSimulations: number;
  activeSimulations: number;
  reportsGenerated: number;
  playbooksAvailable: number;
}

export interface ChatMessage {
  id: string;
  simulationId: string;
  agentId?: string;
  agentName?: string;
  agentColor?: string;
  content: string;
  timestamp: string;
  isUser: boolean;
  context?: string;
  /** Recipient chosen when the user sent this message; null = all agents. Used for Retry. */
  targetAgentId?: string | null;
  /** Client-only: last delivery attempt failed (show Retry). */
  sendFailed?: boolean;
}

export interface BookmarkData {
  id: string;
  round: number;
  label: string;
  note?: string;
  createdAt: string;
}
