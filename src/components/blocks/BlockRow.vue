<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import { formatHours, formatTime } from '../../composables/useFormatting';
import SyncStatusBadge from '../shared/SyncStatusBadge.vue';
import ConfidenceBadge from '../shared/ConfidenceBadge.vue';
import BlockEditor from './BlockEditor.vue';
import { Check, RefreshCw, Pencil, X } from 'lucide-vue-next';

const props = defineProps<{ block: ActivityBlock }>();
const blocksStore = useBlocksStore();
const editing = ref(false);
const retrying = ref(false);

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

function confirm() {
  blocksStore.confirmBlock(props.block.id);
}

function remove() {
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
  <tr class="block-row" :class="{ pending: block.status === 'auto' || block.status === 'closed', confirmed: block.status === 'confirmed', synced: block.status === 'synced', 'has-error': block.status === 'error' }">
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
        class="btn-sm btn-confirm"
        @click="confirm"
        title="Confirmar bloque"
      >
        <Check :size="13" :stroke-width="2.5" />
      </button>
      <button
        v-if="block.status === 'error'"
        class="btn-sm btn-retry"
        @click="retry"
        :disabled="retrying"
        :title="block.sync_error ? `Reintentar (Error: ${block.sync_error})` : 'Reintentar'"
      >
        <RefreshCw :size="13" :stroke-width="2" />
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-edit"
        @click="editing = !editing"
        :title="editing ? 'Cerrar editor' : 'Editar bloque'"
      >
        <Pencil :size="13" :stroke-width="2" />
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-delete"
        @click="remove"
        title="Eliminar bloque"
      >
        <X :size="13" :stroke-width="2" />
      </button>
    </td>
  </tr>
  <tr v-if="editing" class="editor-row">
    <td colspan="9">
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
  font-size: 12px;
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
  font-size: 12px;
}

.no-task {
  color: var(--text-secondary);
}

.col-actions {
  white-space: nowrap;
}

.btn-sm {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-sm);
  padding: 4px;
  cursor: pointer;
  margin-right: 2px;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-sm:disabled {
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

.btn-retry {
  background: var(--warning-soft);
  color: var(--warning);
}

.btn-retry:hover:not(:disabled) {
  background: var(--warning);
  color: #1a1d26;
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

.editor-row td {
  padding: 0 8px 8px;
  border-bottom: 1px solid var(--border);
}
</style>
