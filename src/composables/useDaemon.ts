import { onMounted, onUnmounted } from 'vue';
import { useDaemonStore } from '../stores/daemon';

/**
 * Composable para mantener la conexión con el daemon.
 * Hace polling periódico del estado.
 */
export function useDaemon(intervalMs = 10000) {
  const store = useDaemonStore();
  let timer: ReturnType<typeof setInterval> | null = null;

  onMounted(() => {
    store.fetchStatus();
    timer = setInterval(() => store.fetchStatus(), intervalMs);
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });

  return store;
}
