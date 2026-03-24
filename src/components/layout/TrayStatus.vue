<script setup lang="ts">
import { useDaemonStore } from '../../stores/daemon';

const daemonStore = useDaemonStore();
</script>

<template>
  <div class="tray-status">
    <span class="mode-badge" :class="daemonStore.status.mode">
      {{ daemonStore.modeLabel }}
    </span>
    <span class="blocks-count" v-if="daemonStore.status.running">
      {{ daemonStore.status.blocks_today }} bloques hoy
    </span>
  </div>
</template>

<style scoped>
.tray-status {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.mode-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
}

.mode-badge.active {
  background: var(--success-soft);
  color: var(--success);
}

.mode-badge.silent {
  background: var(--warning-soft);
  color: var(--warning);
}

.mode-badge.paused {
  background: var(--error-soft);
  color: var(--error);
}
</style>
