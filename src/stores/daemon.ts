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
  const captureVersion = ref('');
  const serverVersion = ref('');
  const versionMismatch = ref(false);
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
        serverVersion.value = status.value.version || '';
        checkVersionMismatch();
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
      const result = await api.getCaptureHealth() as { version?: string } | boolean;
      if (typeof result === 'object' && result !== null) {
        captureConnected.value = true;
        captureVersion.value = result.version || '';
        checkVersionMismatch();
      } else {
        captureConnected.value = Boolean(result);
      }
      return captureConnected.value;
    } catch {
      captureConnected.value = false;
      return false;
    }
  }

  function checkVersionMismatch() {
    if (serverVersion.value && captureVersion.value) {
      versionMismatch.value = serverVersion.value !== captureVersion.value;
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
    captureVersion,
    serverVersion,
    versionMismatch,
    fetchStatus,
    healthCheck,
    captureHealthCheck,
    setMode,
  };
});
