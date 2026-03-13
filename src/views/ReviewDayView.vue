<script setup lang="ts">
import { onMounted, watch, ref } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import BlockTable from '../components/blocks/BlockTable.vue';

const blocksStore = useBlocksStore();
const syncing = ref(false);
const syncMessage = ref('');
const syncMessageType = ref<'success' | 'error'>('success');

onMounted(() => {
  blocksStore.fetchBlocks();
});

watch(() => blocksStore.selectedDate, () => {
  blocksStore.fetchBlocks();
});

function confirmAll() {
  const pending = blocksStore.blocks.filter(b => b.status === 'auto');
  pending.forEach(b => blocksStore.confirmBlock(b.id));
}

async function syncToOdoo() {
  syncing.value = true;
  syncMessage.value = '';
  try {
    await blocksStore.syncToOdoo();
    const synced = blocksStore.syncedBlocks.length;
    syncMessage.value = `${synced} bloque(s) sincronizado(s) con Odoo`;
    syncMessageType.value = 'success';
  } catch (e) {
    syncMessage.value = `Error: ${e}`;
    syncMessageType.value = 'error';
  } finally {
    syncing.value = false;
  }
}

function refresh() {
  blocksStore.fetchBlocks();
}
</script>

<template>
  <div class="review-day">
    <div class="review-toolbar">
      <input
        type="date"
        v-model="blocksStore.selectedDate"
        class="date-picker"
      />
      <div class="toolbar-stats">
        <span>{{ blocksStore.blocks.length }} bloques</span>
        <span class="separator">|</span>
        <span>{{ blocksStore.totalHoursToday.toFixed(1) }}h total</span>
        <span v-if="blocksStore.pendingBlocks.length > 0" class="separator">|</span>
        <span v-if="blocksStore.pendingBlocks.length > 0" class="pending-count">
          {{ blocksStore.pendingBlocks.length }} pendientes
        </span>
      </div>
      <div class="toolbar-actions">
        <button class="btn btn-ghost" @click="refresh" title="Refrescar">
          ↻
        </button>
        <button
          class="btn btn-secondary"
          @click="confirmAll"
          :disabled="blocksStore.blocks.filter(b => b.status === 'auto').length === 0"
        >
          Confirmar todos
        </button>
        <button
          class="btn btn-primary"
          @click="syncToOdoo"
          :disabled="blocksStore.blocks.filter(b => b.status === 'confirmed').length === 0 || syncing"
        >
          {{ syncing ? 'Enviando...' : 'Enviar a Odoo' }}
        </button>
      </div>
    </div>

    <div v-if="syncMessage" class="sync-banner" :class="syncMessageType">
      {{ syncMessage }}
    </div>

    <div v-if="blocksStore.error" class="error-banner">
      {{ blocksStore.error }}
    </div>

    <div v-if="blocksStore.loading" class="loading">Cargando bloques...</div>

    <BlockTable v-else :blocks="blocksStore.blocks" />
  </div>
</template>

<style scoped>
.review-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.date-picker {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
}

.toolbar-stats {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.separator {
  margin: 0 6px;
  color: var(--border);
}

.pending-count {
  color: var(--warning);
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  padding: 4px 8px;
}

.btn-ghost:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.sync-banner {
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 12px;
}

.sync-banner.success {
  background: rgba(78, 201, 176, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.sync-banner.error {
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
}

.error-banner {
  padding: 10px 14px;
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  border-radius: 4px;
  color: var(--error);
  font-size: 13px;
  margin-bottom: 12px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
