import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { TimesheetEntry } from '../lib/types';
import { api } from '../lib/api';

export type GroupBy = 'date' | 'project';

export interface TimesheetGroup {
  label: string;
  hours: number;
  entries: TimesheetEntry[];
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

  const grouped = computed((): Record<string, TimesheetGroup> => {
    return groupBy.value === 'date' ? byDate.value : byProject.value;
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
    grouped,
    fetchEntries,
  };
});
