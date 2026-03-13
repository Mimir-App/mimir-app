import { ref, watch } from 'vue';
import type { OdooProject, OdooTask } from '../lib/types';

/**
 * Composable para cargar proyectos y tareas de Odoo.
 */
export function useOdooProjects() {
  const projects = ref<OdooProject[]>([]);
  const tasks = ref<OdooTask[]>([]);
  const selectedProjectId = ref<number | null>(null);
  const loading = ref(false);

  async function loadProjects() {
    loading.value = true;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      projects.value = await invoke<OdooProject[]>('get_odoo_projects');
    } catch {
      projects.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function loadTasks(projectId: number) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      tasks.value = await invoke<OdooTask[]>('get_odoo_tasks', { projectId });
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

  return { projects, tasks, selectedProjectId, loading, loadProjects };
}
