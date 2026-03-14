import { ref, watch } from 'vue';
import type { OdooProject, OdooTask } from '../lib/types';
import { api } from '../lib/api';

/**
 * Composable para cargar proyectos y tareas de Odoo.
 * Usa la capa de abstraccion api.ts (Tauri invoke o HTTP directo).
 */
export function useOdooProjects() {
  const projects = ref<OdooProject[]>([]);
  const tasks = ref<OdooTask[]>([]);
  const selectedProjectId = ref<number | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadProjects() {
    loading.value = true;
    error.value = null;
    try {
      projects.value = await api.getOdooProjects() as OdooProject[];
    } catch (e) {
      projects.value = [];
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  async function loadTasks(projectId: number) {
    try {
      tasks.value = await api.getOdooTasks(projectId) as OdooTask[];
    } catch {
      tasks.value = [];
    }
  }

  watch(selectedProjectId, (newId) => {
    if (newId) {
      loadTasks(newId);
    } else {
      tasks.value = [];
    }
  });

  return { projects, tasks, selectedProjectId, loading, error, loadProjects };
}
