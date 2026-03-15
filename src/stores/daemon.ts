import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { DaemonStatus, DaemonMode } from '../lib/types';
import { api } from '../lib/api';

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
  const captureConnected = ref(false);
  const error = ref<string | null>(null);
  const checking = ref(false);

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
      const result = await api.getDaemonStatus() as DaemonStatus;
      status.value = result;
      connected.value = true;
      error.value = null;
    } catch (e) {
      connected.value = false;
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function healthCheck(): Promise<boolean> {
    checking.value = true;
    try {
      const ok = await api.healthCheck();
      connected.value = ok;
      if (ok) {
        error.value = null;
        await fetchStatus();
      }
      return ok;
    } catch (e) {
      connected.value = false;
      error.value = e instanceof Error ? e.message : String(e);
      return false;
    } finally {
      checking.value = false;
    }
  }

  async function captureHealthCheck(): Promise<boolean> {
    try {
      const ok = await api.captureHealthCheck();
      captureConnected.value = ok;
      return ok;
    } catch {
      captureConnected.value = false;
      return false;
    }
  }

  async function setMode(mode: DaemonMode) {
    try {
      await api.setDaemonMode(mode);
      status.value.mode = mode;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  return {
    status,
    connected,
    error,
    checking,
    statusClass,
    statusText,
    modeLabel,
    captureConnected,
    fetchStatus,
    healthCheck,
    captureHealthCheck,
    setMode,
  };
});
