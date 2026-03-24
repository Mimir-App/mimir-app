import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { AppConfig } from '../lib/types';
import { api } from '../lib/api';

const DEFAULT_CONFIG: AppConfig = {
  daemon_port: 9477,
  gitlab_url: '',
  gitlab_token_stored: false,
  github_token_stored: false,
  odoo_url: '',
  odoo_version: 'v16',
  odoo_db: '',
  odoo_username: '',
  odoo_token_stored: false,
  theme: 'dark',
  refresh_interval_seconds: 300,
  daily_hour_target: 8,
  weekly_hour_targets: [8, 8, 8, 8, 8, 0, 0] as [number, number, number, number, number, number, number],
  ai_provider: 'none',
  ai_api_key_stored: false,
  ai_user_role: 'technical',
  ai_custom_context: '',
  hour_format: 'hm',
  date_format: 'eu',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  font_size: 14,
  dashboard_order: [] as string[],
  dashboard_spans: {} as Record<string, [number, number]>,
  column_widths: {} as Record<string, number>,
  signals_retention_days: 180,
  blocks_retention_days: 365,
  google_client_id: '',
  google_client_secret: '',
  capture_window: true,
  capture_git: true,
  capture_idle: true,
  capture_audio: true,
  capture_ssh: true,
  inactivity_threshold_minutes: 5,
  gitlab_priority_labels: [],
  issue_notes_count: 5,
  dashboard_widgets: [],
  notification_enabled: true,
  notification_interval_minutes: 5,
  notification_retention_days: 7,
  notification_comments: true,
  notification_pipeline_failed: true,
  notification_mr_approved: true,
  notification_changes_requested: true,
  notification_conflicts: true,
  notification_todos: true,
  odoo_refresh_interval_minutes: 60,
};

export const useConfigStore = defineStore('config', () => {
  const config = ref<AppConfig>({ ...DEFAULT_CONFIG });
  const loaded = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    try {
      const result = await api.getConfig() as AppConfig;
      config.value = { ...DEFAULT_CONFIG, ...result };
      loaded.value = true;
      error.value = null;
    } catch (e) {
      config.value = { ...DEFAULT_CONFIG };
      loaded.value = true;
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function save(updates: Partial<AppConfig>) {
    saving.value = true;
    error.value = null;
    try {
      const newConfig = { ...config.value, ...updates };
      await api.saveConfig(newConfig);
      config.value = newConfig;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function setGitLabToken(token: string) {
    await api.storeCredential('gitlab', token);
    config.value.gitlab_token_stored = true;
    await api.saveConfig(config.value);
  }

  async function deleteGitLabToken() {
    await api.deleteCredential('gitlab');
    config.value.gitlab_token_stored = false;
    await api.saveConfig(config.value);
  }

  async function setGitHubToken(token: string) {
    await api.storeCredential('github', token);
    config.value.github_token_stored = true;
    await api.saveConfig(config.value);
  }

  async function deleteGitHubToken() {
    await api.deleteCredential('github');
    config.value.github_token_stored = false;
    await api.saveConfig(config.value);
  }

  async function setOdooToken(token: string) {
    await api.storeCredential('odoo', token);
    config.value.odoo_token_stored = true;
    await api.saveConfig(config.value);
  }

  async function deleteOdooToken() {
    await api.deleteCredential('odoo');
    config.value.odoo_token_stored = false;
    await api.saveConfig(config.value);
  }

  async function pushToDaemon(): Promise<{ status: string; message?: string }> {
    try {
      const result = await api.pushConfigToDaemon(config.value) as { status: string; message?: string };
      return result ?? { status: 'ok' };
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      return { status: 'error', message: msg };
    }
  }

  async function getIntegrationStatus(): Promise<Record<string, unknown>> {
    try {
      return await api.getIntegrationStatus() as Record<string, unknown>;
    } catch {
      return {};
    }
  }

  async function setAIToken(token: string) {
    await api.storeCredential('ai', token);
    config.value.ai_api_key_stored = true;
    await api.saveConfig(config.value);
  }

  async function deleteAIToken() {
    await api.deleteCredential('ai');
    config.value.ai_api_key_stored = false;
    await api.saveConfig(config.value);
  }

  return {
    config,
    loaded,
    saving,
    error,
    load,
    save,
    setGitLabToken,
    deleteGitLabToken,
    setGitHubToken,
    deleteGitHubToken,
    setOdooToken,
    deleteOdooToken,
    setAIToken,
    deleteAIToken,
    pushToDaemon,
    getIntegrationStatus,
  };
});
