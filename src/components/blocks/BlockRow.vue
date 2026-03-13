<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import SyncStatusBadge from '../shared/SyncStatusBadge.vue';
import ConfidenceBadge from '../shared/ConfidenceBadge.vue';
import BlockEditor from './BlockEditor.vue';

const props = defineProps<{ block: ActivityBlock }>();
const blocksStore = useBlocksStore();
const editing = ref(false);

const startTime = computed(() => {
  const d = new Date(props.block.start_time);
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
});

const endTime = computed(() => {
  const d = new Date(props.block.end_time);
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
});

const duration = computed(() => {
  const mins = props.block.duration_minutes;
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return h > 0 ? `${h}h${m.toString().padStart(2, '0')}m` : `${m}m`;
});

const description = computed(() =>
  props.block.user_description ?? props.block.ai_description ?? '—'
);

const canEdit = computed(() =>
  props.block.status !== 'synced'
);

function confirm() {
  blocksStore.confirmBlock(props.block.id);
}

function remove() {
  blocksStore.deleteBlock(props.block.id);
}
</script>

<template>
  <tr class="block-row" :class="{ synced: block.status === 'synced' }">
    <td>{{ startTime }}</td>
    <td>{{ endTime }}</td>
    <td class="col-duration">{{ duration }}</td>
    <td class="col-app">
      <span class="app-name">{{ block.app_name }}</span>
    </td>
    <td class="col-desc">
      <span class="description">{{ description }}</span>
      <ConfidenceBadge
        v-if="block.ai_confidence != null && !block.user_description"
        :confidence="block.ai_confidence"
      />
    </td>
    <td>{{ block.odoo_project_name ?? '—' }}</td>
    <td>{{ block.odoo_task_name ?? '—' }}</td>
    <td><SyncStatusBadge :status="block.status" /></td>
    <td class="col-actions">
      <button
        v-if="block.status === 'auto'"
        class="btn-sm btn-confirm"
        @click="confirm"
        title="Confirmar bloque"
      >
        ✓
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-edit"
        @click="editing = !editing"
        title="Editar bloque"
      >
        ✎
      </button>
      <button
        v-if="canEdit"
        class="btn-sm btn-delete"
        @click="remove"
        title="Eliminar bloque"
      >
        ✕
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

.block-row.synced td {
  opacity: 0.6;
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
  display: flex;
  align-items: center;
  gap: 6px;
}

.description {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.btn-confirm {
  background: var(--success);
  color: white;
}

.btn-confirm:hover {
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
