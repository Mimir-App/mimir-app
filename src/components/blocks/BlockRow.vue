<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import { formatHours, formatTime } from '../../composables/useFormatting';
import SyncStatusBadge from '../shared/SyncStatusBadge.vue';
import ConfidenceBadge from '../shared/ConfidenceBadge.vue';
import BlockEditor from './BlockEditor.vue';
import { Check, RefreshCw, Pencil, Trash2 } from 'lucide-vue-next';

const props = withDefaults(defineProps<{
  block: ActivityBlock;
  selected?: boolean;
  selectable?: boolean;
}>(), {
  selected: false,
  selectable: true,
});
const emit = defineEmits<{ 'toggle-select': [] }>();
const blocksStore = useBlocksStore();
const editing = ref(false);
const retrying = ref(false);
const justConfirmed = ref(false);
const confirmingDelete = ref(false);

const startTime = computed(() => formatTime(props.block.start_time));
const endTime = computed(() => formatTime(props.block.end_time));
const duration = computed(() => formatHours(props.block.duration_minutes / 60));

const description = computed(() =>
  props.block.user_description ?? props.block.ai_description ?? ''
);

const canEdit = computed(() =>
  props.block.status !== 'synced'
);

const canConfirm = computed(() =>
  props.block.status === 'auto' || props.block.status === 'closed'
);

async function confirm() {
  await blocksStore.confirmBlock(props.block.id);
  justConfirmed.value = true;
  setTimeout(() => { justConfirmed.value = false; }, 1200);
}

function requestDelete() {
  confirmingDelete.value = true;
  setTimeout(() => { confirmingDelete.value = false; }, 3000);
}

function confirmDelete() {
  confirmingDelete.value = false;
  blocksStore.deleteBlock(props.block.id);
}

async function retry() {
  retrying.value = true;
  try {
    await blocksStore.retrySync(props.block.id);
  } catch {
    // El store ya refresca el estado
  } finally {
    retrying.value = false;
  }
}
</script>

<template>
  <tr class="block-row" :class="{ pending: block.status === 'auto' || block.status === 'closed', confirmed: block.status === 'confirmed', synced: block.status === 'synced', 'has-error': block.status === 'error', 'is-selected': selected }">
    <td class="col-select">
      <input
        v-if="selectable"
        type="checkbox"
        :checked="selected"
        @change="emit('toggle-select')"
        :aria-label="`Seleccionar bloque ${startTime} - ${endTime}`"
      />
    </td>
    <td>{{ startTime }}</td>
    <td>{{ endTime }}</td>
    <td class="col-duration">{{ duration }}</td>
    <td class="col-app">
      <span class="app-name" :title="block.app_name">{{ block.app_name }}</span>
    </td>
    <td class="col-desc">
      <span v-if="description" class="description">{{ description }}</span>
      <span v-else class="no-desc">Sin descripcion</span>
      <ConfidenceBadge
        v-if="block.ai_confidence != null && !block.user_description"
        :confidence="block.ai_confidence"
      />
    </td>
    <td>
      <span v-if="block.odoo_project_name" class="project-name">{{ block.odoo_project_name }}</span>
      <span v-else class="no-project">Sin proyecto</span>
    </td>
    <td>
      <span v-if="block.odoo_task_name">{{ block.odoo_task_name }}</span>
      <span v-else class="no-task">&mdash;</span>
    </td>
    <td>
      <SyncStatusBadge :status="block.status" :error="block.sync_error" />
    </td>
    <td class="col-actions">
      <button
        v-if="canConfirm"
        class="btn-action btn-confirm"
        :class="{ 'just-confirmed': justConfirmed }"
        @click="confirm"
        :title="justConfirmed ? 'Confirmado' : 'Confirmar bloque'"
        :aria-label="justConfirmed ? 'Bloque confirmado' : 'Confirmar bloque'"
      >
        <Check :size="13" :stroke-width="2.5" />
      </button>
      <button
        v-if="block.status === 'error'"
        class="btn-action btn-retry"
        @click="retry"
        :disabled="retrying"
        :class="{ spinning: retrying }"
        :title="block.sync_error ? `Reintentar (Error: ${block.sync_error})` : 'Reintentar'"
        aria-label="Reintentar sincronizacion"
      >
        <RefreshCw :size="13" :stroke-width="2" />
      </button>
      <button
        v-if="canEdit"
        class="btn-action btn-edit"
        @click="editing = !editing"
        :title="editing ? 'Cerrar editor' : 'Editar bloque'"
        :aria-label="editing ? 'Cerrar editor' : 'Editar bloque'"
      >
        <Pencil :size="13" :stroke-width="2" />
      </button>
      <button
        v-if="canEdit && !confirmingDelete"
        class="btn-action btn-delete"
        @click="requestDelete"
        title="Eliminar bloque"
        aria-label="Eliminar bloque"
      >
        <Trash2 :size="13" :stroke-width="2" />
      </button>
      <button
        v-if="confirmingDelete"
        class="btn-action btn-delete-confirm"
        @click="confirmDelete"
        title="Confirmar eliminacion"
        aria-label="Confirmar eliminacion del bloque"
      >
        <Trash2 :size="13" :stroke-width="2" />
        <span class="confirm-text">Eliminar</span>
      </button>
    </td>
  </tr>
  <tr v-if="editing" class="editor-row">
    <td colspan="10">
      <BlockEditor :block="block" @close="editing = false" />
    </td>
  </tr>
</template>

<style scoped>
.block-row td {
  padding: var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
  transition: background var(--duration-fast);
}

.block-row:hover td {
  background: var(--bg-hover);
}

.block-row.pending td {
  opacity: 0.5;
}

.block-row.confirmed td {
  opacity: 0.9;
}

.block-row.synced td {
  opacity: 0.55;
}

.block-row.has-error td {
  background: var(--error-soft);
}

.col-duration {
  font-variant-numeric: tabular-nums;
}

.app-name {
  display: inline-block;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-desc {
  max-width: 300px;
}

.description {
  display: inline;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-desc {
  color: var(--text-secondary);
  font-style: italic;
  font-size: var(--text-xs);
}

.project-name {
  display: inline-block;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-project {
  color: var(--text-secondary);
  font-style: italic;
  font-size: var(--text-xs);
}

.no-task {
  color: var(--text-secondary);
}

.col-actions {
  white-space: nowrap;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-sm);
  padding: var(--space-1);
  cursor: pointer;
  margin-right: 2px;
  transition: all var(--duration-fast) var(--ease-out);
  gap: var(--space-1);
}

.btn-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-confirm {
  background: var(--success-soft);
  color: var(--success);
}

.btn-confirm:hover {
  background: var(--success);
  color: white;
}

.btn-confirm.just-confirmed {
  background: var(--success);
  color: white;
  animation: pulse-confirm 0.4s var(--ease-spring);
}

@keyframes pulse-confirm {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

.btn-retry {
  background: var(--warning-soft);
  color: var(--warning);
}

.btn-retry:hover:not(:disabled) {
  background: var(--warning);
  color: #1a1d26;
}

.btn-retry.spinning :deep(svg) {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.btn-edit {
  background: transparent;
  color: var(--text-secondary);
}

.btn-edit:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-delete {
  background: transparent;
  color: var(--text-muted);
}

.btn-delete:hover {
  background: var(--error-soft);
  color: var(--error);
}

.btn-delete-confirm {
  background: var(--error);
  color: white;
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-2);
  animation: shake 0.3s var(--ease-out);
}

.btn-delete-confirm:hover {
  background: #dc2626;
}

.confirm-text {
  font-size: var(--text-xs);
  font-weight: 500;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

.editor-row td {
  padding: 0 var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--border);
}

.col-select {
  width: 32px;
  text-align: center;
  padding: var(--space-2) var(--space-1);
}

.col-select input[type="checkbox"] {
  cursor: pointer;
  accent-color: var(--accent);
}

.block-row.is-selected td {
  background: var(--accent-soft);
}
</style>
