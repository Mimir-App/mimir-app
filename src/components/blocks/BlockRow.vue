<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import { formatHours, formatTime } from '../../composables/useFormatting';
import SyncStatusBadge from '../shared/SyncStatusBadge.vue';
import ConfidenceBadge from '../shared/ConfidenceBadge.vue';
import BlockEditor from './BlockEditor.vue';

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
        &#x2713;
      </button>
      <button
        v-if="block.status === 'error'"
        class="btn-sm btn-retry"
        @click="retry"
        :disabled="retrying"
        :title="block.sync_error ? `Reintentar (Error: ${block.sync_error})` : 'Reintentar'"
      >
        &#x21bb;
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-edit"
        @click="editing = !editing"
        :title="editing ? 'Cerrar editor' : 'Editar bloque'"
      >
        &#x270E;
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-delete"
        @click="remove"
        title="Eliminar bloque"
      >
        &#x2715;
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
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.block-row:hover td {
  background: var(--bg-hover);
}

.block-row.pending td {
  opacity: 0.5;
}

.block-row.confirmed td {
  opacity: 0.85;
}

.block-row.synced td {
  opacity: 0.6;
}

.block-row.has-error td {
  background: rgba(241, 76, 76, 0.03);
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
  border: none;
  border-radius: 3px;
  padding: 2px 6px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 2px;
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-confirm {
  background: var(--success);
  color: white;
}

.btn-confirm:hover {
  opacity: 0.85;
}

.btn-retry {
  background: var(--warning);
  color: #1e2029;
}

.btn-retry:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-edit {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-edit:hover {
  background: var(--bg-hover);
}

.btn-delete {
  background: transparent;
  color: var(--error);
}

.btn-delete:hover {
  background: rgba(241, 76, 76, 0.15);
}

.editor-row td {
  padding: 0 8px 8px;
  border-bottom: 1px solid var(--border);
}
</style>
