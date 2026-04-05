// Audit trail types

export type AuditEventType =
  | 'config_change'
  | 'simulation_start'
  | 'simulation_pause'
  | 'simulation_resume'
  | 'simulation_complete'
  | 'agent_decision'
  | 'report_generation'
  | 'annotation_added'
  | 'parameter_change'
  | 'export';

export interface AuditEvent {
  event_id: string;
  simulation_id: string;
  event_type: AuditEventType;
  timestamp: string;
  actor: string;
  details: Record<string, unknown>;
  previous_hash: string;
  hash: string;
}

export interface AuditTrail {
  simulation_id: string;
  events: AuditEvent[];
  is_valid: boolean;
  integrity_check_message: string;
}

export interface AuditVerifyResult {
  valid: boolean;
  message: string;
}
