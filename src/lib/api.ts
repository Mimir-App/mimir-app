/**
 * Capa de abstraccion para comunicacion con el daemon.
 * En Tauri: usa invoke() (proxy Rust -> daemon HTTP).
 * En navegador: llama directamente al daemon HTTP en localhost:9477.
 */

import type { ItemPreference, GitLabIssue, GitLabMergeRequest, GitLabLabel, GitLabNote, MRConflict, GitLabTodo, AppNotification, ContextMapping } from './types';

const DAEMON_BASE = 'http://127.0.0.1:9477';

let _isTauri: boolean | null = null;

async function isTauri(): Promise<boolean> {
  if (_isTauri !== null) return _isTauri;
  try {
    // window.__TAURI_INTERNALS__ exists when running inside Tauri
    _isTauri = !!(window as any).__TAURI_INTERNALS__;
  } catch {
    _isTauri = false;
  }
  return _isTauri;
}

async function tauriInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<T>(command, args);
}

async function httpGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${DAEMON_BASE}${path}`);
  if (!resp.ok) throw new Error(`Daemon responded ${resp.status}`);
  return resp.json();
}

async function httpPost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${DAEMON_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw new Error(`Daemon responded ${resp.status}`);
  return resp.json();
}

async function httpPut<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${DAEMON_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw new Error(`Daemon responded ${resp.status}`);
  return resp.json();
}

async function httpDelete(path: string): Promise<void> {
  const resp = await fetch(`${DAEMON_BASE}${path}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Daemon responded ${resp.status}`);
}

// --- API publica ---

export const api = {
  async getDaemonStatus() {
    if (await isTauri()) return tauriInvoke('get_daemon_status');
    return httpGet('/status');
  },

  async healthCheck(): Promise<boolean> {
    if (await isTauri()) return tauriInvoke<boolean>('daemon_health_check');
    try {
      await httpGet('/health');
      return true;
    } catch {
      return false;
    }
  },

  async captureHealthCheck(): Promise<boolean> {
    if (await isTauri()) return tauriInvoke<boolean>('capture_health_check');
    try {
      const resp = await fetch('http://127.0.0.1:9476/health');
      return resp.ok;
    } catch {
      return false;
    }
  },

  async getCaptureHealth(): Promise<{ version?: string } | null> {
    if (await isTauri()) return tauriInvoke('get_capture_health');
    try {
      const resp = await fetch('http://127.0.0.1:9476/health');
      if (!resp.ok) return null;
      return resp.json();
    } catch {
      return null;
    }
  },

  async setDaemonMode(mode: string) {
    if (await isTauri()) return tauriInvoke('set_daemon_mode', { mode });
    return httpPost('/mode', { mode });
  },

  async getBlocks(date: string) {
    if (await isTauri()) return tauriInvoke('get_blocks', { date });
    return httpGet(`/blocks?date=${date}`);
  },

  async confirmBlock(blockId: number) {
    if (await isTauri()) return tauriInvoke('confirm_block', { blockId });
    return httpPost(`/blocks/${blockId}/confirm`);
  },

  async updateBlock(blockId: number, updates: Record<string, unknown>) {
    if (await isTauri()) return tauriInvoke('update_block', { blockId, updates });
    return httpPut(`/blocks/${blockId}`, updates);
  },

  async deleteBlock(blockId: number) {
    if (await isTauri()) return tauriInvoke('delete_block', { blockId });
    return httpDelete(`/blocks/${blockId}`);
  },

  async syncBlocks(blockIds: number[]) {
    if (await isTauri()) return tauriInvoke('sync_blocks_to_odoo', { blockIds });
    return httpPost('/blocks/sync', { block_ids: blockIds });
  },

  async retrySync(blockId: number) {
    if (await isTauri()) return tauriInvoke('retry_sync_block', { blockId });
    return httpPost(`/blocks/${blockId}/retry`);
  },

  async getSignals(date?: string, blockId?: number) {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (blockId) params.set('block_id', String(blockId));
    if (await isTauri()) return tauriInvoke('get_signals', { date, blockId });
    return httpGet(`/signals?${params}`);
  },

  async splitBlock(blockId: number, signalId: number) {
    if (await isTauri()) return tauriInvoke('split_block', { blockId, signalId });
    return httpPost(`/blocks/${blockId}/split?signal_id=${signalId}`);
  },

  async mergeBlocks(blockIds: number[]) {
    if (await isTauri()) return tauriInvoke('merge_blocks', { blockIds });
    return httpPost('/blocks/merge', { block_ids: blockIds });
  },

  // Google Calendar
  async getGoogleAuthUrl() {
    if (await isTauri()) return tauriInvoke('get_google_auth_url');
    return httpGet('/google/calendar/auth-url');
  },

  async getGoogleCalendarStatus() {
    if (await isTauri()) return tauriInvoke('get_google_calendar_status');
    return httpGet('/google/calendar/status');
  },

  async disconnectGoogleCalendar() {
    if (await isTauri()) return tauriInvoke('disconnect_google_calendar');
    return httpPost('/google/calendar/disconnect');
  },

  async getContextMappings(): Promise<ContextMapping[]> {
    if (await isTauri()) return tauriInvoke('get_context_mappings');
    return httpGet('/context-mappings');
  },

  async suggestMapping(contextKey: string): Promise<ContextMapping | null> {
    if (await isTauri()) return tauriInvoke('suggest_context_mapping', { contextKey });
    try {
      return await httpGet(`/context-mappings/suggest?context_key=${encodeURIComponent(contextKey)}`);
    } catch {
      return null;
    }
  },

  async saveContextMapping(mapping: ContextMapping) {
    if (await isTauri()) return tauriInvoke('save_context_mapping', { mapping });
    return httpPut('/context-mappings', mapping);
  },

  async deleteContextMapping(contextKey: string) {
    if (await isTauri()) return tauriInvoke('delete_context_mapping', { contextKey });
    return httpDelete(`/context-mappings/${encodeURIComponent(contextKey)}`);
  },

  async getOdooProjects() {
    if (await isTauri()) return tauriInvoke('get_odoo_projects');
    return httpGet('/odoo/projects');
  },

  async getOdooTasks(projectId: number) {
    if (await isTauri()) return tauriInvoke('get_odoo_tasks', { projectId });
    return httpGet(`/odoo/tasks/${projectId}`);
  },

  async searchOdooTasks(query: string, limit: number = 10) {
    if (await isTauri()) return tauriInvoke('search_odoo_tasks', { query, limit });
    return httpGet(`/odoo/tasks/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  },

  async getTimesheetEntries(dateFrom: string, dateTo: string) {
    if (await isTauri()) return tauriInvoke('get_timesheet_entries', { dateFrom, dateTo });
    return httpGet(`/odoo/entries?from=${dateFrom}&to=${dateTo}`);
  },

  async getIssues() {
    if (await isTauri()) return tauriInvoke('get_issues');
    return httpGet('/gitlab/issues');
  },

  async getMergeRequests() {
    if (await isTauri()) return tauriInvoke('get_merge_requests');
    return httpGet('/gitlab/merge_requests');
  },

  // Config y auth solo funcionan en Tauri (usan filesystem/keyring local)
  async getConfig() {
    if (await isTauri()) return tauriInvoke('get_config');
    // En navegador, devolver config por defecto
    return {
      daemon_port: 9477,
      gitlab_url: '',
      gitlab_token_stored: false,
      odoo_url: '',
      odoo_version: 'v16',
      odoo_db: '',
      odoo_username: '',
      odoo_token_stored: false,
      theme: 'dark',
      refresh_interval_seconds: 300,
      daily_hour_target: 8,
      weekly_hour_targets: [8, 8, 8, 8, 8, 0, 0],
      ai_provider: 'none',
      ai_api_key_stored: false,
      ai_user_role: 'technical',
      ai_custom_context: '',
      hour_format: 'hm',
      date_format: 'eu',
      font_size: 14,
      dashboard_order: [],
      dashboard_spans: {} as Record<string, [number, number]>,
      column_widths: {},
    };
  },

  async saveConfig(config: unknown) {
    if (await isTauri()) return tauriInvoke('save_config', { config });
    console.warn('[api] saveConfig: no disponible fuera de Tauri');
  },

  async storeCredential(service: string, token: string) {
    if (await isTauri()) return tauriInvoke('store_credential', { service, token });
    console.warn('[api] storeCredential: no disponible fuera de Tauri');
  },

  async getCredential(service: string): Promise<string | null> {
    if (await isTauri()) return tauriInvoke<string | null>('get_credential', { service });
    return null;
  },

  async deleteCredential(service: string) {
    if (await isTauri()) return tauriInvoke('delete_credential', { service });
    console.warn('[api] deleteCredential: no disponible fuera de Tauri');
  },

  async pushConfigToDaemon(config: unknown) {
    if (await isTauri()) return tauriInvoke('push_config_to_daemon', { config });
    // En navegador, enviar directamente al daemon
    return httpPut('/config', config);
  },

  async generateDescription(blockId: number) {
    if (await isTauri()) return tauriInvoke('generate_block_description', { blockId });
    return httpPost(`/blocks/${blockId}/generate-description`);
  },

  async getIntegrationStatus() {
    if (await isTauri()) return tauriInvoke('get_integration_status');
    return httpGet('/config/integration-status');
  },

  // Attendance
  async getAttendanceToday() {
    if (await isTauri()) return tauriInvoke('get_attendance_today');
    return httpGet('/odoo/attendance/today');
  },

  async attendanceCheckIn() {
    if (await isTauri()) return tauriInvoke('attendance_check_in');
    return httpPost('/odoo/attendance/checkin');
  },

  async attendanceCheckOut(attendanceId: number) {
    if (await isTauri()) return tauriInvoke('attendance_check_out', { attendanceId });
    return httpPost(`/odoo/attendance/${attendanceId}/checkout`);
  },

  // Service control
  async startCapture() {
    if (await isTauri()) return tauriInvoke('start_capture_service');
  },
  async stopCapture() {
    if (await isTauri()) return tauriInvoke('stop_capture_service');
  },
  async restartCapture() {
    if (await isTauri()) return tauriInvoke('restart_capture_service');
  },
  async startServer() {
    if (await isTauri()) return tauriInvoke('start_server_service');
  },
  async stopServer() {
    if (await isTauri()) return tauriInvoke('stop_server_service');
  },
  async restartServer() {
    if (await isTauri()) return tauriInvoke('restart_server_service');
  },

  async getItemPreferences(type: string): Promise<ItemPreference[]> {
    if (await isTauri()) return tauriInvoke('get_item_preferences', { itemType: type });
    return httpGet(`/items/preferences?type=${type}`);
  },

  async updateItemPreferences(type: string, id: number, body: Partial<ItemPreference>): Promise<void> {
    if (await isTauri()) return tauriInvoke('update_item_preferences', { itemType: type, itemId: id, body });
    return httpPut(`/items/${type}/${id}/preferences`, body);
  },

  async searchGitlabIssues(q: string): Promise<GitLabIssue[]> {
    if (await isTauri()) return tauriInvoke('search_gitlab_issues', { q });
    return httpGet(`/gitlab/issues/search?q=${encodeURIComponent(q)}`);
  },

  async searchGithubIssues(q: string): Promise<GitLabIssue[]> {
    if (await isTauri()) return tauriInvoke('search_github_issues', { q });
    return httpGet(`/github/issues/search?q=${encodeURIComponent(q)}`);
  },

  async searchGithubPullRequests(q: string): Promise<GitLabMergeRequest[]> {
    if (await isTauri()) return tauriInvoke('search_github_pull_requests', { q });
    return httpGet(`/github/pull_requests/search?q=${encodeURIComponent(q)}`);
  },

  async getFollowedIssues(): Promise<GitLabIssue[]> {
    if (await isTauri()) return tauriInvoke('get_followed_issues');
    return httpGet('/gitlab/issues/followed');
  },

  async getGitlabLabels(): Promise<GitLabLabel[]> {
    if (await isTauri()) return tauriInvoke('get_gitlab_labels');
    return httpGet('/gitlab/labels');
  },

  async getIssueNotes(projectId: string, issueIid: number, perPage: number = 5): Promise<GitLabNote[]> {
    if (await isTauri()) return tauriInvoke('get_issue_notes', { projectId, issueIid, perPage });
    return httpGet(`/gitlab/issues/${projectId}/${issueIid}/notes?per_page=${perPage}`);
  },

  async getGithubIssueComments(owner: string, repo: string, issueNumber: number, perPage: number = 5): Promise<GitLabNote[]> {
    if (await isTauri()) return tauriInvoke('get_github_issue_comments', { owner, repo, issueNumber, perPage });
    return httpGet(`/github/issues/${owner}/${repo}/${issueNumber}/comments?per_page=${perPage}`);
  },

  async updateTimesheetEntry(entryId: number, body: { description?: string; hours?: number; project_id?: number; task_id?: number }): Promise<void> {
    if (await isTauri()) return tauriInvoke('update_timesheet_entry', { entryId, body });
    return httpPut(`/odoo/entries/${entryId}`, body);
  },

  async searchMergeRequests(q: string): Promise<GitLabMergeRequest[]> {
    if (await isTauri()) return tauriInvoke('search_gitlab_merge_requests', { q });
    return httpGet(`/gitlab/merge_requests/search?q=${encodeURIComponent(q)}`);
  },
  async getFollowedMergeRequests(): Promise<GitLabMergeRequest[]> {
    if (await isTauri()) return tauriInvoke('get_followed_merge_requests');
    return httpGet('/gitlab/merge_requests/followed');
  },
  async getMRNotes(projectId: string, mrIid: number, perPage: number = 5): Promise<GitLabNote[]> {
    if (await isTauri()) return tauriInvoke('get_mr_notes', { projectId, mrIid, perPage });
    return httpGet(`/gitlab/merge_requests/${projectId}/${mrIid}/notes?per_page=${perPage}`);
  },
  async getMRConflicts(projectId: string, mrIid: number): Promise<MRConflict[]> {
    if (await isTauri()) return tauriInvoke('get_mr_conflicts', { projectId, mrIid });
    return httpGet(`/gitlab/merge_requests/${projectId}/${mrIid}/conflicts`);
  },
  async getGitlabTodos(): Promise<GitLabTodo[]> {
    if (await isTauri()) return tauriInvoke('get_gitlab_todos');
    return httpGet('/gitlab/todos');
  },
  async getGitlabUser(): Promise<{ id: number; username: string; name: string }> {
    if (await isTauri()) return tauriInvoke('get_gitlab_user');
    return httpGet('/gitlab/user');
  },
  async githubOAuthStart(): Promise<{ device_code: string; user_code: string; verification_uri: string; expires_in: number; interval: number; error?: string }> {
    if (await isTauri()) return tauriInvoke('github_oauth_start');
    return httpPost('/github/oauth/start', {});
  },
  async githubOAuthPoll(deviceCode: string): Promise<{ status: string; access_token?: string; interval?: number; error?: string }> {
    if (await isTauri()) return tauriInvoke('github_oauth_poll', { body: { device_code: deviceCode } });
    return httpPost('/github/oauth/poll', { device_code: deviceCode });
  },
  async getNotifications(unreadOnly: boolean = true): Promise<AppNotification[]> {
    if (await isTauri()) return tauriInvoke('get_notifications', { unreadOnly });
    return httpGet(`/notifications?unread_only=${unreadOnly}`);
  },
  async getNotificationCount(): Promise<{ count: number }> {
    if (await isTauri()) return tauriInvoke('get_notification_count');
    return httpGet('/notifications/count');
  },
  async markNotificationRead(id: number): Promise<void> {
    if (await isTauri()) return tauriInvoke('mark_notification_read', { notificationId: id });
    return httpPut(`/notifications/${id}/read`, {});
  },
  async markAllNotificationsRead(): Promise<void> {
    if (await isTauri()) return tauriInvoke('mark_all_notifications_read');
    return httpPut('/notifications/read-all', {});
  },
};
