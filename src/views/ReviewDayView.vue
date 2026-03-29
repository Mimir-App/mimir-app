<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import { useDaemonStore } from '../stores/daemon';
import { formatHours, formatTime } from '../composables/useFormatting';
import { api } from '../lib/api';
import type { TimesheetEntry } from '../lib/types';
import BlockTable from '../components/blocks/BlockTable.vue';
import ReviewPanel from '../components/blocks/ReviewPanel.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import StatusBanner from '../components/shared/StatusBanner.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import CustomDatePicker from '../components/shared/CustomDatePicker.vue';
import { ChevronLeft, ChevronRight, RefreshCw, CheckCheck, Send, Clock, CheckCircle2, AlertTriangle, Upload, Sparkles, Loader2, ClipboardCheck } from 'lucide-vue-next';

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
  blocksStore.clearReview();
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

async function generateBlocks() {
  syncMessage.value = '';
  try {
    await blocksStore.generateBlocks();
    syncMessage.value = 'Bloques generados correctamente';
    syncMessageType.value = 'success';
    fetchOdooEntries();
  } catch (e) {
    syncMessage.value = `Error generando bloques: ${blocksStore.generateError || e}`;
    syncMessageType.value = 'error';
  }
}

async function reviewBlocks() {
  syncMessage.value = '';
  try {
    await blocksStore.reviewBlocks();
  } catch {
    syncMessage.value = `Error revisando bloques: ${blocksStore.reviewError}`;
    syncMessageType.value = 'error';
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
        <button class="btn btn-ghost btn-icon" @click="prevDay" title="Día anterior">
          <ChevronLeft :size="16" :stroke-width="2" />
        </button>
        <CustomDatePicker v-model="blocksStore.selectedDate" />
        <button class="btn btn-ghost btn-icon" @click="nextDay" title="Día siguiente">
          <ChevronRight :size="16" :stroke-width="2" />
        </button>
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
        <span class="stat-item">{{ blocksStore.blocks.length }} bloques</span>
        <span class="separator">|</span>
        <span class="stat-item">{{ formatHours(blocksStore.totalHoursToday) }} total</span>
        <template v-if="autoBlocksCount > 0">
          <span class="separator">|</span>
          <span class="stat-item pending-count"><Clock :size="12" :stroke-width="2" /> {{ autoBlocksCount }} pendientes</span>
        </template>
        <template v-if="confirmedCount > 0">
          <span class="separator">|</span>
          <span class="stat-item confirmed-count"><CheckCircle2 :size="12" :stroke-width="2" /> {{ confirmedCount }} confirmados</span>
        </template>
        <template v-if="errorCount > 0">
          <span class="separator">|</span>
          <span class="stat-item error-count"><AlertTriangle :size="12" :stroke-width="2" /> {{ errorCount }} con error</span>
        </template>
        <template v-if="syncedCount > 0">
          <span class="separator">|</span>
          <span class="stat-item synced-count"><Upload :size="12" :stroke-width="2" /> {{ syncedCount }} enviados</span>
        </template>
        <template v-if="odooEntries.length > 0">
          <span class="separator">|</span>
          <span class="stat-item odoo-count">Odoo: {{ formatHours(odooTotalHours) }}</span>
        </template>
      </div>
      <div class="toolbar-actions">
        <button class="btn btn-ghost btn-icon" @click="refresh" title="Refrescar">
          <RefreshCw :size="15" :stroke-width="2" />
        </button>
        <button
          class="btn btn-generate"
          @click="generateBlocks"
          :disabled="blocksStore.generating"
          title="Genera bloques analizando señales, actividad VCS y calendario"
          aria-label="Generar bloques de imputación"
        >
          <Loader2 v-if="blocksStore.generating" :size="15" :stroke-width="2" class="spin" />
          <Sparkles v-else :size="15" :stroke-width="2" />
          {{ blocksStore.generating ? 'Generando...' : 'Generar bloques' }}
        </button>
        <button
          class="btn btn-review"
          @click="reviewBlocks"
          :disabled="blocksStore.reviewing || blocksStore.blocks.length === 0 || blocksStore.generating"
          title="Revisa los bloques generados con IA"
          aria-label="Revisar bloques de imputacion"
        >
          <Loader2 v-if="blocksStore.reviewing" :size="15" :stroke-width="2" class="spin" />
          <ClipboardCheck v-else :size="15" :stroke-width="2" />
          {{ blocksStore.reviewing ? 'Revisando...' : 'Revisar' }}
        </button>
        <button
          class="btn btn-secondary"
          @click="confirmAll"
          :disabled="autoBlocksCount === 0"
        >
          <CheckCheck :size="15" :stroke-width="2" />
          Confirmar todos
        </button>
        <button
          class="btn btn-primary"
          @click="syncToOdoo"
          :disabled="confirmedCount === 0 || syncing || !odooConnected"
          :title="!odooConnected ? 'Daemon no conectado' : ''"
        >
          <Send :size="14" :stroke-width="2" />
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

    <StatusBanner v-if="blocksStore.generating" type="info">
      Analizando señales, actividad VCS y calendario... Esto puede tardar 2-3 minutos.
    </StatusBanner>

    <StatusBanner v-if="blocksStore.reviewing" type="info">
      Revisando bloques... Esto puede tardar 2-3 minutos.
    </StatusBanner>

    <ReviewPanel
      v-if="blocksStore.reviewResult"
      :result="blocksStore.reviewResult"
      @dismiss="blocksStore.clearReview()"
    />

    <LoadingState v-if="blocksStore.loading && !blocksStore.generating" text="Cargando bloques..." />

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
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.date-nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.btn-today {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-2);
  color: var(--accent);
  font-weight: 500;
}

.toolbar-stats {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.separator {
  margin: 0 6px;
  color: var(--border);
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pending-count { color: var(--warning); }
.confirmed-count { color: var(--info); }
.error-count { color: var(--error); }
.synced-count { color: var(--success); }

.odoo-count {
  color: var(--accent);
  font-weight: 500;
}

.toolbar-actions {
  display: flex;
  gap: var(--space-2);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--duration-base) var(--ease-out);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: white;
  box-shadow: 0 2px 8px var(--accent-glow);
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: 0 4px 16px var(--accent-glow);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--text-muted);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  padding: var(--space-2);
}

.btn-ghost:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.btn-icon {
  padding: 6px;
  border-radius: var(--radius-md);
}

.btn-generate {
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  color: white;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}

.btn-generate:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.4);
  transform: translateY(-1px);
}

.btn-generate:disabled {
  opacity: 0.7;
}

.btn-review {
  background: linear-gradient(135deg, #059669, #0d9488);
  color: white;
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3);
}

.btn-review:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(5, 150, 105, 0.4);
  transform: translateY(-1px);
}

.btn-review:disabled {
  opacity: 0.7;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}

/* ── Tables ── */
.odoo-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.odoo-table th {
  text-align: left;
  padding: var(--space-3) var(--space-2);
  color: var(--text-muted);
  font-weight: 600;
  font-size: var(--text-xs);
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.odoo-table td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
}

.odoo-row td {
  opacity: 0.85;
  transition: background var(--duration-fast);
}

.odoo-row:hover td {
  background: var(--bg-hover);
}

.odoo-table .col-project { min-width: 120px; }
.odoo-table .col-task { min-width: 120px; }
.odoo-table .col-hours { text-align: right; min-width: 60px; font-variant-numeric: tabular-nums; }

/* Signals table */
.signals-table-wrap { overflow-x: auto; }
.signals-table { width: 100%; font-size: var(--text-xs); border-collapse: collapse; }
.signals-table th { text-align: left; padding: var(--space-1) var(--space-2); color: var(--text-muted); border-bottom: 1px solid var(--border); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; font-size: 10px; }
.signals-table td { padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--border-subtle); transition: background var(--duration-fast); }
.signals-table tr:hover td { background: var(--bg-hover); }
.signal-title { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.context-badge { font-size: 10px; padding: 2px 6px; border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-secondary); font-family: var(--font-mono); }
.signals-empty { padding: var(--space-4); text-align: center; color: var(--text-muted); font-size: var(--text-sm); }
</style>
