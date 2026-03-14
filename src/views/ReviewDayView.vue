<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import { useDaemonStore } from '../stores/daemon';
import BlockTable from '../components/blocks/BlockTable.vue';

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();
const syncing = ref(false);
const syncMessage = ref('');
const syncMessageType = ref<'success' | 'error'>('success');

const autoBlocksCount = computed(() =>
  blocksStore.blocks.filter(b => b.status === 'auto' || b.status === 'closed').length
);

const confirmedCount = computed(() =>
  blocksStore.confirmedBlocks.length
);

const errorCount = computed(() =>
  blocksStore.errorBlocks.length
);

const syncedCount = computed(() =>
  blocksStore.syncedBlocks.length
);

const odooConnected = computed(() => daemonStore.connected);

onMounted(() => {
  blocksStore.fetchBlocks();
});

watch(() => blocksStore.selectedDate, () => {
  blocksStore.fetchBlocks();
  syncMessage.value = '';
});

async function confirmAll() {
  const pending = blocksStore.blocks.filter(b => b.status === 'auto' || b.status === 'closed');
  for (const b of pending) {
    try {
      await blocksStore.confirmBlock(b.id);
    } catch {
      // Continuar con el siguiente
    }
  }
}

async function syncToOdoo() {
  syncing.value = true;
  syncMessage.value = '';
  try {
    const result = await blocksStore.syncToOdoo();
    if (result) {
      const { synced, errors } = result;
      if (errors.length === 0) {
        syncMessage.value = `${synced} bloque(s) sincronizado(s) con Odoo`;
        syncMessageType.value = 'success';
      } else {
        syncMessage.value = `${synced} sincronizado(s), ${errors.length} error(es)`;
        syncMessageType.value = errors.length > 0 && synced === 0 ? 'error' : 'success';
      }
    }
  } catch (e) {
    syncMessage.value = `Error: ${e}`;
    syncMessageType.value = 'error';
  } finally {
    syncing.value = false;
  }
}

function refresh() {
  syncMessage.value = '';
  blocksStore.fetchBlocks();
}

function prevDay() {
  const d = new Date(blocksStore.selectedDate);
  d.setDate(d.getDate() - 1);
  blocksStore.selectedDate = d.toISOString().slice(0, 10);
}

function nextDay() {
  const d = new Date(blocksStore.selectedDate);
  d.setDate(d.getDate() + 1);
  blocksStore.selectedDate = d.toISOString().slice(0, 10);
}

function goToday() {
  blocksStore.selectedDate = new Date().toISOString().slice(0, 10);
}

const isToday = computed(() =>
  blocksStore.selectedDate === new Date().toISOString().slice(0, 10)
);
</script>

<template>
  <div class="review-day">
    <div class="review-toolbar">
      <div class="date-nav">
        <button class="btn btn-ghost" @click="prevDay" title="Dia anterior">&lt;</button>
        <input
          type="date"
          v-model="blocksStore.selectedDate"
          class="date-picker"
        />
        <button class="btn btn-ghost" @click="nextDay" title="Dia siguiente">&gt;</button>
        <button
          v-if="!isToday"
          class="btn btn-ghost btn-today"
          @click="goToday"
          title="Ir a hoy"
        >
          Hoy
        </button>
      </div>
      <div class="toolbar-stats">
        <span>{{ blocksStore.blocks.length }} bloques</span>
        <span class="separator">|</span>
        <span>{{ blocksStore.totalHoursToday.toFixed(1) }}h total</span>
        <template v-if="autoBlocksCount > 0">
          <span class="separator">|</span>
          <span class="pending-count">{{ autoBlocksCount }} pendientes</span>
        </template>
        <template v-if="confirmedCount > 0">
          <span class="separator">|</span>
          <span class="confirmed-count">{{ confirmedCount }} confirmados</span>
        </template>
        <template v-if="errorCount > 0">
          <span class="separator">|</span>
          <span class="error-count">{{ errorCount }} con error</span>
        </template>
        <template v-if="syncedCount > 0">
          <span class="separator">|</span>
          <span class="synced-count">{{ syncedCount }} enviados</span>
        </template>
      </div>
      <div class="toolbar-actions">
        <button class="btn btn-ghost" @click="refresh" title="Refrescar">
          &#x21bb;
        </button>
        <button
          class="btn btn-secondary"
          @click="confirmAll"
          :disabled="autoBlocksCount === 0"
        >
          Confirmar todos
        </button>
        <button
          class="btn btn-primary"
          @click="syncToOdoo"
          :disabled="confirmedCount === 0 || syncing || !odooConnected"
          :title="!odooConnected ? 'Daemon no conectado' : ''"
        >
          {{ syncing ? 'Enviando...' : `Enviar a Odoo (${confirmedCount})` }}
        </button>
      </div>
    </div>

    <div v-if="syncMessage" class="sync-banner" :class="syncMessageType">
      {{ syncMessage }}
      <button class="banner-close" @click="syncMessage = ''">&times;</button>
    </div>

    <div v-if="blocksStore.error" class="error-banner">
      {{ blocksStore.error }}
    </div>

    <div v-if="!odooConnected && blocksStore.blocks.length > 0" class="warning-banner">
      Daemon no conectado. Los bloques se pueden revisar pero no enviar a Odoo.
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

.date-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.date-picker {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
}

.btn-today {
  font-size: 12px;
  padding: 4px 8px;
  color: var(--accent);
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

.confirmed-count {
  color: #569cd6;
}

.error-count {
  color: var(--error);
}

.synced-count {
  color: var(--success);
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
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.banner-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0.7;
}

.banner-close:hover {
  opacity: 1;
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

.warning-banner {
  padding: 10px 14px;
  background: rgba(220, 220, 170, 0.1);
  border: 1px solid var(--warning);
  border-radius: 4px;
  color: var(--warning);
  font-size: 13px;
  margin-bottom: 12px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
