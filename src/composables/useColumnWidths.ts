import { ref } from 'vue';
import { useConfigStore } from '../stores/config';

/**
 * Anchos de columna globales compartidos entre todas las tablas.
 * Se persisten en config.
 */

export const DEFAULT_COLUMN_WIDTHS: Record<string, number> = {
  time: 65,
  duration: 70,
  app: 140,
  description: 250,
  project: 160,
  task: 160,
  status: 80,
  actions: 60,
  score: 55,
  iid: 45,
  labels: 180,
  assignee: 100,
  date: 100,
  branch: 150,
  pipeline: 80,
  conflicts: 70,
  hours: 70,
};

const resizing = ref<string | null>(null);
const startX = ref(0);
const startWidth = ref(0);

export function useColumnWidths() {
  const configStore = useConfigStore();

  function getWidth(col: string): number {
    const saved = configStore.config.column_widths;
    if (saved && saved[col]) return saved[col];
    return DEFAULT_COLUMN_WIDTHS[col] ?? 100;
  }

  function setWidth(col: string, width: number) {
    const clamped = Math.max(40, Math.min(600, width));
    if (!configStore.config.column_widths) {
      configStore.config.column_widths = {};
    }
    configStore.config.column_widths[col] = clamped;
  }

  function saveWidths() {
    configStore.save(configStore.config);
  }

  function resetWidths() {
    configStore.config.column_widths = {};
    configStore.save(configStore.config);
  }

  function startResize(col: string, e: MouseEvent) {
    e.preventDefault();
    resizing.value = col;
    startX.value = e.clientX;
    startWidth.value = getWidth(col);

    const onMove = (ev: MouseEvent) => {
      if (!resizing.value) return;
      const delta = ev.clientX - startX.value;
      setWidth(resizing.value, startWidth.value + delta);
    };

    const onUp = () => {
      resizing.value = null;
      saveWidths();
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  function colStyle(col: string): Record<string, string> {
    return {
      width: `${getWidth(col)}px`,
      minWidth: `${getWidth(col)}px`,
      maxWidth: `${getWidth(col)}px`,
    };
  }

  return { getWidth, setWidth, startResize, colStyle, resetWidths, resizing };
}
