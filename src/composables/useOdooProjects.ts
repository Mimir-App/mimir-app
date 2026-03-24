import { ref, watch, computed } from 'vue';
import type { OdooTask } from '../lib/types';
import { useOdooStore } from '../stores/odoo';

/**
 * Composable para cargar proyectos y tareas de Odoo.
 * Delega al store central que mantiene cache con refresh periodico.
 */
export function useOdooProjects() {
  const odooStore = useOdooStore();
  const projects = computed(() => odooStore.projects);
  const tasks = ref<OdooTask[]>([]);
  const selectedProjectId = ref<number | null>(null);
  const loading = computed(() => odooStore.loading);
  const error = computed(() => odooStore.error);

  async function loadProjects() {
    await odooStore.fetchProjects();
  }

  watch(selectedProjectId, async (newId) => {
    if (newId) {
      tasks.value = await odooStore.fetchTasks(newId);
    } else {
      tasks.value = [];
    }
  });

  return { projects, tasks, selectedProjectId, loading, error, loadProjects };
}
