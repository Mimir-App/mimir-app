import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { TimesheetEntry } from '../lib/types';
import { api } from '../lib/api';

export type GroupBy = 'date' | 'project' | 'task' | 'week';

export interface TimesheetGroup {
  label: string;
  hours: number;
  entries: TimesheetEntry[];
}

function getISOWeek(date: Date): number {
  const d = new Date(date.getTime());
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7));
  const yearStart = new Date(d.getFullYear(), 0, 4);
  return 1 + Math.round(((d.getTime() - yearStart.getTime()) / 86400000 - 3 + ((yearStart.getDay() + 6) % 7)) / 7);
}

export const useTimesheetsStore = defineStore('timesheets', () => {
  const entries = ref<TimesheetEntry[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const dateFrom = ref(new Date().toISOString().slice(0, 10));
  const dateTo = ref(new Date().toISOString().slice(0, 10));
  const groupBy = ref<GroupBy>('date');

  const totalHours = computed(() =>
    entries.value.reduce((sum, e) => sum + e.hours, 0)
  );

  const byProject = computed((): Record<string, TimesheetGroup> => {
    const groups: Record<string, TimesheetGroup> = {};
    for (const entry of entries.value) {
      const key = entry.project_name || 'Sin proyecto';
      if (!groups[key]) {
        groups[key] = { label: key, hours: 0, entries: [] };
      }
      groups[key].hours += entry.hours;
      groups[key].entries.push(entry);
    }
    return groups;
  });

  const byDate = computed((): Record<string, TimesheetGroup> => {
    const groups: Record<string, TimesheetGroup> = {};
    for (const entry of entries.value) {
      const key = entry.date;
      if (!groups[key]) {
        groups[key] = { label: key, hours: 0, entries: [] };
      }
      groups[key].hours += entry.hours;
      groups[key].entries.push(entry);
    }
    // Ordenar por fecha descendente
    const sorted: Record<string, TimesheetGroup> = {};
    for (const key of Object.keys(groups).sort().reverse()) {
      sorted[key] = groups[key];
    }
    return sorted;
  });

  const byTask = computed((): Record<string, TimesheetGroup> => {
    const groups: Record<string, TimesheetGroup> = {};
    for (const entry of entries.value) {
      const key = entry.task_name
        ? `${entry.project_name} / ${entry.task_name}`
        : entry.project_name || 'Sin tarea';
      if (!groups[key]) {
        groups[key] = { label: key, hours: 0, entries: [] };
      }
      groups[key].hours += entry.hours;
      groups[key].entries.push(entry);
    }
    return groups;
  });

  const byWeek = computed((): Record<string, TimesheetGroup> => {
    const groups: Record<string, TimesheetGroup> = {};
    for (const entry of entries.value) {
      const d = new Date(entry.date + 'T00:00:00');
      const dayOfWeek = d.getDay() || 7; // lunes=1, domingo=7
      const monday = new Date(d);
      monday.setDate(d.getDate() - dayOfWeek + 1);
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      const weekNum = getISOWeek(d);
      const key = monday.toISOString().slice(0, 10);
      const label = `Semana ${weekNum} — ${monday.toISOString().slice(0, 10)} al ${sunday.toISOString().slice(0, 10)}`;
      if (!groups[key]) {
        groups[key] = { label, hours: 0, entries: [] };
      }
      groups[key].hours += entry.hours;
      groups[key].entries.push(entry);
    }
    const sorted: Record<string, TimesheetGroup> = {};
    for (const key of Object.keys(groups).sort().reverse()) {
      sorted[key] = groups[key];
    }
    return sorted;
  });

  const grouped = computed((): Record<string, TimesheetGroup> => {
    switch (groupBy.value) {
      case 'project': return byProject.value;
      case 'task': return byTask.value;
      case 'week': return byWeek.value;
      default: return byDate.value;
    }
  });

  async function fetchEntries(from?: string, to?: string) {
    loading.value = true;
    error.value = null;
    try {
      entries.value = await api.getTimesheetEntries(
        from ?? dateFrom.value,
        to ?? dateTo.value,
      ) as TimesheetEntry[];
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  return {
    entries,
    loading,
    error,
    dateFrom,
    dateTo,
    groupBy,
    totalHours,
    byProject,
    byDate,
    byTask,
    byWeek,
    grouped,
    fetchEntries,
  };
});
