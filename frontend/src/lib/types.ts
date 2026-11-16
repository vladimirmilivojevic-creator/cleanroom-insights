// TypeScript mirrors of the FastAPI (Pydantic) response models.

export type Role = "admin" | "trainer" | "trainee";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Me extends User {
  organization_id: number;
  organization_name: string;
}

export interface Module {
  code: string;
  title: string;
  description: string;
  steps: { code: string; title: string }[];
  deviations: Deviation[];
}

export interface Deviation {
  code: string;
  title: string;
  severity: "minor" | "major" | "critical";
}

export interface SessionEvent {
  id: number;
  kind: "step" | "deviation";
  step: string;
  deviation: string | null;
  severity: Deviation["severity"] | null;
  penalty: number;
  created_at: string;
}

export interface TrainingSession {
  id: number;
  module: string;
  status: "running" | "completed";
  trainee_id: number;
  trainee_name: string;
  started_at: string;
  finished_at: string | null;
  score: number | null;
  passed: boolean | null;
}

export interface SessionDetail extends TrainingSession {
  events: SessionEvent[];
  certificate_code: string | null;
}

export interface Certificate {
  code: string;
  module: string;
  score: number;
  issued_at: string;
  valid_until: string;
  trainee_id: number;
  trainee_name: string;
}

export interface CertificateVerification extends Certificate {
  organization_name: string;
  valid: boolean;
}

export interface Overview {
  trainees: number;
  completed_sessions: number;
  running_sessions: number;
  pass_rate: number;
  average_score: number;
  valid_certificates: number;
}

export interface Heatmap {
  module: string;
  steps: { code: string; title: string }[];
  deviations: Deviation[];
  cells: { step: string; deviation: string; count: number }[];
}

export interface TraineeProgress {
  trainee_id: number;
  trainee_name: string;
  sessions: number;
  average_score: number | null;
  last_score: number | null;
  passed_sessions: number;
  certified_modules: string[];
}

export interface TraineeDetail {
  trainee: User;
  sessions: TrainingSession[];
  certificates: Certificate[];
}

export interface WarehouseReport {
  last_run: { finished_at: string; sessions: number; events: number } | null;
  weekly: { week: string; sessions: number; average_score: number; pass_rate: number }[];
  modules: { module: string; sessions: number; average_score: number; pass_rate: number }[];
  top_deviations: { deviation: string; severity: string; occurrences: number; total_penalty: number }[];
}

export interface AuditEntry {
  id: number;
  actor_id: number | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
  hash: string;
}

export interface AuditVerification {
  valid: boolean;
  checked: number;
  broken_at_id: number | null;
}

// Messages pushed over the live-session WebSocket
export type LiveMessage =
  | { type: "subscribed"; channel: string }
  | { type: "event"; event: SessionEvent }
  | { type: "finished"; session: TrainingSession; certificate_code: string | null };
