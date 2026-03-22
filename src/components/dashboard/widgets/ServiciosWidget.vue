<script setup lang="ts">
import { useDaemonStore } from '../../../stores/daemon';
import { useBlocksStore } from '../../../stores/blocks';
import { Radio, Server, Layers } from 'lucide-vue-next';

defineProps<{ config: Record<string, any> }>();

const daemonStore = useDaemonStore();
const blocksStore = useBlocksStore();
</script>

<template>
  <div class="widget-services">
    <h3 class="widget-title">Servicios</h3>
    <div class="service-list">
      <div class="service-row">
        <div class="service-icon-wrap">
          <Radio :size="14" :stroke-width="2" />
        </div>
        <span class="service-name">Captura</span>
        <span class="service-status" :class="daemonStore.captureConnected ? 'active' : 'inactive'">
          <span class="status-indicator"></span>
          {{ daemonStore.captureConnected ? 'Activo' : 'Inactivo' }}
        </span>
      </div>
      <div class="service-row">
        <div class="service-icon-wrap">
          <Server :size="14" :stroke-width="2" />
        </div>
        <span class="service-name">Servidor</span>
        <span class="service-status" :class="daemonStore.connected ? 'active' : 'inactive'">
          <span class="status-indicator"></span>
          {{ daemonStore.connected ? 'Activo' : 'Inactivo' }}
        </span>
      </div>
      <div class="service-row">
        <div class="service-icon-wrap">
          <Layers :size="14" :stroke-width="2" />
        </div>
        <span class="service-name">Bloques hoy</span>
        <span class="service-count">{{ blocksStore.blocks.length }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget-services {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.widget-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.service-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--duration-fast);
}

.service-row:hover {
  background: var(--bg-hover);
}

.service-icon-wrap {
  color: var(--text-muted);
  display: flex;
  align-items: center;
}

.service-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.service-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 500;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  transition: background var(--duration-base), box-shadow var(--duration-base);
}

.service-status.active {
  color: var(--success);
}

.service-status.active .status-indicator {
  background: var(--success);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.4);
}

.service-status.inactive {
  color: var(--error);
}

.service-status.inactive .status-indicator {
  background: var(--error);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.3);
}

.service-count {
  font-size: var(--text-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
