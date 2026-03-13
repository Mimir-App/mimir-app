import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { DaemonStatus, DaemonMode } from '../lib/types';

export const useDaemonStore = defineStore('daemon', () => {
  const status = ref<DaemonStatus>({
    running: false,
    mode: 'active',
    uptime_seconds: 0,
    last_poll: null,
    blocks_today: 0,
    version: '0.1.0',
  });

  const connected = ref(false);
  const error = ref<string | null>(null);

  const statusClass = computed(() =>
    connected.value ? 'connected' : 'disconnected'
  );

  const statusText = computed(() =>
    connected.value ? `Daemon v${status.value.version}` : 'Desconectado'
  );

  const modeLabel = computed(() => {
    const labels: Record<DaemonMode, string> = {
      active: 'Activo',
      silent: 'Silencio',
      paused: 'Pausado',
    };
    return labels[status.value.mode];
  });

  async function fetchStatus() {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const result = await invoke<DaemonStatus>('get_daemon_status');
      status.value = result;
      connected.value = true;
      error.value = null;
    } catch (e) {
      connected.value = false;
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function setMode(mode: DaemonMode) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_daemon_mode', { mode });
      status.value.mode = mode;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  return {
    status,
    connected,
    error,
    statusClass,
    statusText,
    modeLabel,
    fetchStatus,
    setMode,
  };
});
