import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import type { OdooProject, OdooTask } from '../lib/types';
import { api } from '../lib/api';
import { useConfigStore } from './config';

export const useOdooStore = defineStore('odoo', () => {
  const projects = ref<OdooProject[]>([]);
  const tasksCache = ref<Map<number, OdooTask[]>>(new Map());
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastRefresh = ref<number>(0);
  let timer: ReturnType<typeof setInterval> | null = null;

  async function fetchProjects() {
    loading.value = true;
    error.value = null;
    try {
      projects.value = await api.getOdooProjects() as OdooProject[];
      // Limpiar cache de tareas para forzar recarga
      tasksCache.value = new Map();
      lastRefresh.value = Date.now();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  async function fetchTasks(projectId: number): Promise<OdooTask[]> {
    const cached = tasksCache.value.get(projectId);
    if (cached) return cached;
    try {
      const tasks = await api.getOdooTasks(projectId) as OdooTask[];
      const updated = new Map(tasksCache.value);
      updated.set(projectId, tasks);
      tasksCache.value = updated;
      return tasks;
    } catch {
      return [];
    }
  }

  function startPolling() {
    stopPolling();
    const configStore = useConfigStore();
    const minutes = configStore.config.odoo_refresh_interval_minutes || 60;
    const ms = minutes * 60 * 1000;

    // Carga inicial si no hay datos
    if (projects.value.length === 0) {
      fetchProjects();
    }

    timer = setInterval(() => {
      fetchProjects();
    }, ms);
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  /** Reinicia el polling cuando cambia el intervalo en config */
  function watchConfig() {
    const configStore = useConfigStore();
    watch(
      () => configStore.config.odoo_refresh_interval_minutes,
      () => {
        if (timer) startPolling();
      },
    );
  }

  return {
    projects,
    tasksCache,
    loading,
    error,
    lastRefresh,
    fetchProjects,
    fetchTasks,
    startPolling,
    stopPolling,
    watchConfig,
  };
});
