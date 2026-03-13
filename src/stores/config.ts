import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { AppConfig } from '../lib/types';

const DEFAULT_CONFIG: AppConfig = {
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

export const useConfigStore = defineStore('config', () => {
  const config = ref<AppConfig>({ ...DEFAULT_CONFIG });
  const loaded = ref(false);

  async function load() {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const result = await invoke<AppConfig>('get_config');
      config.value = result;
      loaded.value = true;
    } catch {
      config.value = { ...DEFAULT_CONFIG };
      loaded.value = true;
    }
  }

  async function save(updates: Partial<AppConfig>) {
    const { invoke } = await import('@tauri-apps/api/core');
    const newConfig = { ...config.value, ...updates };
    await invoke('save_config', { config: newConfig });
    config.value = newConfig;
  }

  async function setGitLabToken(token: string) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('store_credential', { service: 'gitlab', token });
    config.value.gitlab_token_stored = true;
  }

  async function setOdooToken(token: string) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('store_credential', { service: 'odoo', token });
    config.value.odoo_token_stored = true;
  }

  return { config, loaded, load, save, setGitLabToken, setOdooToken };
});
