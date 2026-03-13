<script setup lang="ts">
import { computed } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import SyncStatusBadge from '../shared/SyncStatusBadge.vue';
import ConfidenceBadge from '../shared/ConfidenceBadge.vue';

const props = defineProps<{ block: ActivityBlock }>();
const blocksStore = useBlocksStore();

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
  const m = mins % 60;
  return h > 0 ? `${h}h${m.toString().padStart(2, '0')}m` : `${m}m`;
});

const description = computed(() =>
  props.block.user_description ?? props.block.ai_description ?? '—'
);

function confirm() {
  blocksStore.confirmBlock(props.block.id);
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
    <td>
      <button
        v-if="block.status === 'auto'"
        class="btn-sm"
        @click="confirm"
        title="Confirmar bloque"
      >
        ✓
      </button>
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

.btn-sm {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 3px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: 12px;
}

.btn-sm:hover {
  background: var(--accent-hover);
}
</style>
