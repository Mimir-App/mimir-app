<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import { useDaemonStore } from '../stores/daemon';
import { formatHours, formatTime } from '../composables/useFormatting';
import { api } from '../lib/api';
import type { TimesheetEntry } from '../lib/types';
import BlockTable from '../components/blocks/BlockTable.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import StatusBanner from '../components/shared/StatusBanner.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import CustomDatePicker from '../components/shared/CustomDatePicker.vue';

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();
const odooEntries = ref<TimesheetEntry[]>([]);
const loadingOdoo = ref(false);
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

async function fetchOdooEntries() {
  if (!daemonStore.connected) return;
  loadingOdoo.value = true;
  try {
    const date = blocksStore.selectedDate;
    odooEntries.value = await api.getTimesheetEntries(date, date) as TimesheetEntry[];
  } catch {
    odooEntries.value = [];
  } finally {
    loadingOdoo.value = false;
  }
}

const odooTotalHours = computed(() =>
  odooEntries.value.reduce((sum, e) => sum + e.hours, 0)
);

onMounted(() => {
  blocksStore.fetchBlocks();
  blocksStore.fetchSignals();
  fetchOdooEntries();
});

watch(() => blocksStore.selectedDate, () => {
  blocksStore.fetchBlocks();
  blocksStore.fetchSignals();
  fetchOdooEntries();
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
  fetchOdooEntries();
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
        <CustomDatePicker v-model="blocksStore.selectedDate" />
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
        <span>{{ formatHours(blocksStore.totalHoursToday) }} total</span>
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
        <template v-if="odooEntries.length > 0">
          <span class="separator">|</span>
          <span class="odoo-count">Odoo: {{ formatHours(odooTotalHours) }}</span>
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

    <StatusBanner v-if="syncMessage" :type="syncMessageType" dismissible @dismiss="syncMessage = ''">
      {{ syncMessage }}
    </StatusBanner>

    <StatusBanner v-if="blocksStore.error" type="error">{{ blocksStore.error }}</StatusBanner>

    <StatusBanner v-if="!odooConnected && blocksStore.blocks.length > 0" type="warning">
      Daemon no conectado. Los bloques se pueden revisar pero no enviar a Odoo.
    </StatusBanner>

    <LoadingState v-if="blocksStore.loading" text="Cargando bloques..." />

    <BlockTable v-else :blocks="blocksStore.blocks" />

    <!-- Entradas de Odoo -->
    <CollapsibleGroup
      v-if="odooEntries.length > 0 || loadingOdoo"
      label="Imputaciones en Odoo"
      :count="odooEntries.length"
      :summary="formatHours(odooTotalHours)"
    >
      <LoadingState v-if="loadingOdoo" text="Cargando entradas de Odoo..." />
      <table v-else class="odoo-table">
        <thead>
          <tr>
            <th class="col-project">Proyecto</th>
            <th class="col-task">Tarea</th>
            <th>Descripcion</th>
            <th class="col-hours">Horas</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in odooEntries" :key="entry.id" class="odoo-row">
            <td>{{ entry.project_name }}</td>
            <td>{{ entry.task_name ?? '—' }}</td>
            <td>{{ entry.description }}</td>
            <td class="col-hours">{{ formatHours(entry.hours) }}</td>
          </tr>
        </tbody>
      </table>
    </CollapsibleGroup>

    <!-- Señales crudas -->
    <CollapsibleGroup
      label="Señales crudas"
      :count="blocksStore.signals.length"
    >
      <LoadingState v-if="blocksStore.signalsLoading" text="Cargando señales..." />
      <div v-else-if="blocksStore.signals.length > 0" class="signals-table-wrap">
        <table class="signals-table">
          <thead>
            <tr>
              <th>Hora</th>
              <th>App</th>
              <th>Titulo</th>
              <th>Contexto</th>
              <th>Proyecto</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in blocksStore.signals" :key="s.id">
              <td>{{ formatTime(s.timestamp) }}</td>
              <td>{{ s.app_name }}</td>
              <td class="signal-title">{{ s.window_title }}</td>
              <td><span class="context-badge">{{ s.context_key }}</span></td>
              <td>{{ s.project_path ? s.project_path.split('/').pop() : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="signals-empty">Sin señales para esta fecha</div>
    </CollapsibleGroup>
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

.odoo-count {
  color: var(--accent);
  font-weight: 500;
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

.odoo-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.odoo-table th {
  text-align: left;
  padding: 10px 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.odoo-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.odoo-row td {
  opacity: 0.85;
}

.odoo-row:hover td {
  background: var(--bg-hover);
}

.odoo-table .col-project { min-width: 120px; }
.odoo-table .col-task { min-width: 120px; }
.odoo-table .col-hours { text-align: right; min-width: 60px; }

/* Signals table */
.signals-table-wrap { overflow-x: auto; }
.signals-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.signals-table th { text-align: left; padding: 4px 8px; color: var(--text-secondary); border-bottom: 1px solid var(--border); font-weight: 500; }
.signals-table td { padding: 4px 8px; border-bottom: 1px solid var(--border); }
.signal-title { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.context-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--bg-secondary); color: var(--text-secondary); }
.signals-empty { padding: 16px; text-align: center; color: var(--text-secondary); font-size: 13px; }
</style>
