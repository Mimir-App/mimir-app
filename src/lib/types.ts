/** Tipos compartidos de Mimir */

// --- Bloques de actividad ---

export type BlockStatus = 'auto' | 'closed' | 'confirmed' | 'synced' | 'error';

export interface ActivityBlock {
  id: number;
  start_time: string;       // ISO 8601
  end_time: string;         // ISO 8601
  duration_minutes: number;
  app_name: string;
  window_title: string;
  project_path: string | null;
  git_branch: string | null;
  git_remote: string | null;
  ai_description: string | null;
  ai_confidence: number | null;  // 0.0 - 1.0
  user_description: string | null;
  odoo_project_id: number | null;
  odoo_task_id: number | null;
  odoo_project_name: string | null;
  odoo_task_name: string | null;
  status: BlockStatus;
  sync_error: string | null;
  odoo_entry_id: number | null;
}

// --- Signals ---

export interface Signal {
  id: number;
  timestamp: string;
  app_name: string | null;
  window_title: string | null;
  project_path: string | null;
  git_branch: string | null;
  git_remote: string | null;
  ssh_host: string | null;
  pid: number | null;
  context_key: string | null;
  last_commit_message: string | null;
  idle_ms: number;
  audio_app: string | null;
  is_meeting: boolean;
  workspace: string | null;
  calendar_event: string | null;
  calendar_attendees: string | null;
  created_at: string;
}

// --- GitLab ---

export interface GitLabIssue {
  id: number;
  iid: number;
  title: string;
  description: string | null;
  state: string;
  web_url: string;
  project_path: string;
  labels: string[];
  assignees: GitLabUser[];
  milestone: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  user_notes_count: number;
  has_conflicts: boolean;
  score: number;
  manual_priority: number | null;
}

export interface GitLabMergeRequest {
  id: number;
  iid: number;
  title: string;
  description: string | null;
  state: string;
  web_url: string;
  project_path: string;
  labels: string[];
  assignees: GitLabUser[];
  reviewers: GitLabUser[];
  source_branch: string;
  target_branch: string;
  has_conflicts: boolean;
  pipeline_status: string | null;
  created_at: string;
  updated_at: string;
  user_notes_count: number;
  score: number;
  manual_priority: number | null;
}

export interface GitLabUser {
  id: number;
  username: string;
  name: string;
  avatar_url: string;
}

// --- Odoo ---

export interface OdooProject {
  id: number;
  name: string;
}

export interface OdooTask {
  id: number;
  name: string;
  project_id: number;
}

export interface TimesheetEntry {
  id: number;
  date: string;
  project_id: number;
  project_name: string;
  task_id: number | null;
  task_name: string | null;
  description: string;
  hours: number;
  employee_id: number;
}

// --- Daemon ---

export type DaemonMode = 'active' | 'silent' | 'paused';

export interface DaemonStatus {
  running: boolean;
  mode: DaemonMode;
  uptime_seconds: number;
  last_poll: string | null;
  blocks_today: number;
  version: string;
}

// --- Config ---

export interface AppConfig {
  daemon_port: number;
  gitlab_url: string;
  gitlab_token_stored: boolean;
  odoo_url: string;
  odoo_version: 'v11' | 'v16';
  odoo_db: string;
  odoo_username: string;
  odoo_token_stored: boolean;
  theme: 'dark' | 'light' | 'system';
  refresh_interval_seconds: number;
  daily_hour_target: number; // legacy, se mantiene como fallback
  weekly_hour_targets: [number, number, number, number, number, number, number]; // lun-dom
  ai_provider: 'gemini' | 'claude' | 'openai' | 'none';
  ai_api_key_stored: boolean;
  ai_user_role: 'technical' | 'functional' | 'other';
  ai_custom_context: string;
  hour_format: 'decimal' | 'hm' | 'minutes';
  date_format: 'iso' | 'eu' | 'short' | 'long';
  timezone: string;
  font_size: number;
  dashboard_order: string[];
  dashboard_spans: Record<string, [number, number]>; // [cols, rows]
  column_widths: Record<string, number>;
  // Retencion de datos
  signals_retention_days: number;
  blocks_retention_days: number;
  // Google Calendar
  google_client_id: string;
  google_client_secret: string;
  // Permisos de captura
  capture_window: boolean;
  capture_git: boolean;
  capture_idle: boolean;
  capture_audio: boolean;
  capture_ssh: boolean;
}
