import { onMounted, onUnmounted } from 'vue';
import { useConfigStore } from '../stores/config';

/**
 * Composable para polling periodico.
 * Ejecuta fetchFn al montar y luego cada refresh_interval_seconds.
 * Limpia el timer al desmontar.
 */
export function usePolling(fetchFn: () => void | Promise<void>) {
  const configStore = useConfigStore();
  let timer: ReturnType<typeof setInterval> | null = null;

  function start() {
    stop();
    const interval = (configStore.config.refresh_interval_seconds || 300) * 1000;
    timer = setInterval(fetchFn, interval);
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  onMounted(() => {
    fetchFn();
    start();
  });

  onUnmounted(() => {
    stop();
  });

  return { start, stop };
}
