import { ref, computed, type Ref } from 'vue';

export type SortDir = 'asc' | 'desc';

export function useSortable<T>(items: Ref<T[]>, defaultKey: string = '', defaultDir: SortDir = 'asc') {
  const sortKey = ref(defaultKey);
  const sortDir = ref<SortDir>(defaultDir);

  function toggleSort(key: string) {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey.value = key;
      sortDir.value = 'asc';
    }
  }

  function sortIcon(key: string): string {
    if (sortKey.value !== key) return '';
    return sortDir.value === 'asc' ? ' \u25B2' : ' \u25BC';
  }

  const sorted = computed(() => {
    if (!sortKey.value) return items.value;
    const key = sortKey.value;
    const dir = sortDir.value === 'asc' ? 1 : -1;
    return [...items.value].sort((a, b) => {
      const va = (a as Record<string, unknown>)[key];
      const vb = (b as Record<string, unknown>)[key];
      if (va == null && vb == null) return 0;
      if (va == null) return dir;
      if (vb == null) return -dir;
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
      if (typeof va === 'string' && typeof vb === 'string') return va.localeCompare(vb) * dir;
      if (typeof va === 'boolean' && typeof vb === 'boolean') return ((va ? 1 : 0) - (vb ? 1 : 0)) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  });

  return { sortKey, sortDir, toggleSort, sortIcon, sorted };
}
