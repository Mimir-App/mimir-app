import { onMounted, onUnmounted } from 'vue';
import { useDaemonStore } from '../stores/daemon';
import { useConfigStore } from '../stores/config';

/**
 * Composable para mantener la conexion con el daemon.
 * Hace health check al montar y polling periodico del estado.
 * Usa el intervalo de refresco de la configuracion.
 */
export function useDaemon(intervalMs?: number) {
  const store = useDaemonStore();
  const configStore = useConfigStore();
  let timer: ReturnType<typeof setInterval> | null = null;

  onMounted(async () => {
    // Primero verificar que el daemon esta vivo
    await store.healthCheck();

    // Usar el intervalo de la config o el parametro, con minimo 5s
    const interval = intervalMs ?? Math.max((configStore.config.refresh_interval_seconds ?? 10) * 1000, 5000);

    // Iniciar polling periodico del estado
    store.fetchStatus();
    timer = setInterval(() => store.fetchStatus(), Math.min(interval, 10000));
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });

  return store;
}
