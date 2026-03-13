import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { TimesheetEntry } from '../lib/types';
import { api } from '../lib/api';

export const useTimesheetsStore = defineStore('timesheets', () => {
  const entries = ref<TimesheetEntry[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const dateFrom = ref(new Date().toISOString().slice(0, 10));
  const dateTo = ref(new Date().toISOString().slice(0, 10));

  const totalHours = computed(() =>
    entries.value.reduce((sum, e) => sum + e.hours, 0)
  );

  const byProject = computed(() => {
    const groups: Record<string, { hours: number; entries: TimesheetEntry[] }> = {};
    for (const entry of entries.value) {
      if (!groups[entry.project_name]) {
        groups[entry.project_name] = { hours: 0, entries: [] };
      }
      groups[entry.project_name].hours += entry.hours;
      groups[entry.project_name].entries.push(entry);
    }
    return groups;
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
    totalHours,
    byProject,
    fetchEntries,
  };
});
