<script setup lang="ts">
import { useDaemonStore } from '../../../stores/daemon';
import { useBlocksStore } from '../../../stores/blocks';

defineProps<{ config: Record<string, any> }>();

const daemonStore = useDaemonStore();
const blocksStore = useBlocksStore();
</script>

<template>
  <h3 class="card-title">Servicios</h3>
  <div class="daemon-info">
    <div class="info-row">
      <span class="label">Captura</span>
      <span class="value" :class="daemonStore.captureConnected ? 'connected' : 'disconnected'">
        {{ daemonStore.captureConnected ? 'Activo' : 'Inactivo' }}
      </span>
    </div>
    <div class="info-row">
      <span class="label">Servidor</span>
      <span class="value" :class="daemonStore.statusClass">
        {{ daemonStore.connected ? 'Activo' : 'Inactivo' }}
      </span>
    </div>
    <div class="info-row">
      <span class="label">Bloques hoy</span>
      <span class="value">{{ blocksStore.blocks.length }}</span>
    </div>
  </div>
</template>

<style scoped>
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.daemon-info { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 13px; }
.info-row .label { color: var(--text-secondary); }
.info-row .value.connected { color: var(--success); }
.info-row .value.disconnected { color: var(--error); }
</style>
