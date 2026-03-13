/**
 * Capa de abstraccion para comunicacion con el daemon.
 * En Tauri: usa invoke() (proxy Rust -> daemon HTTP).
 * En navegador: llama directamente al daemon HTTP en localhost:9477.
 */

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

  async getOdooProjects() {
    if (await isTauri()) return tauriInvoke('get_odoo_projects');
    return httpGet('/odoo/projects');
  },

  async getOdooTasks(projectId: number) {
    if (await isTauri()) return tauriInvoke('get_odoo_tasks', { projectId });
    return httpGet(`/odoo/tasks/${projectId}`);
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
};
