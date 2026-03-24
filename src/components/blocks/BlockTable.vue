<script setup lang="ts">
import { toRef, ref, computed } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import { useBlocksStore } from '../../stores/blocks';
import BlockRow from './BlockRow.vue';
import EmptyState from '../shared/EmptyState.vue';
import { GitMerge } from 'lucide-vue-next';

const props = defineProps<{ blocks: ActivityBlock[] }>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'blocks'), 'start_time', 'asc');
const { colStyle, startResize } = useColumnWidths();
const blocksStore = useBlocksStore();

const selectedIds = ref<Set<number>>(new Set());
const merging = ref(false);

const mergeableBlocks = computed(() =>
  sorted.value.filter(b => b.status !== 'synced')
);

const selectedCount = computed(() => selectedIds.value.size);

const allSelected = computed(() =>
  mergeableBlocks.value.length > 0 && mergeableBlocks.value.every(b => selectedIds.value.has(b.id))
);

function toggleSelect(blockId: number) {
  const next = new Set(selectedIds.value);
  if (next.has(blockId)) {
    next.delete(blockId);
  } else {
    next.add(blockId);
  }
  selectedIds.value = next;
}

function toggleAll() {
  if (allSelected.value) {
    selectedIds.value = new Set();
  } else {
    selectedIds.value = new Set(mergeableBlocks.value.map(b => b.id));
  }
}

async function mergeSelected() {
  if (selectedCount.value < 2) return;
  merging.value = true;
  try {
    await blocksStore.mergeBlocks(Array.from(selectedIds.value));
    selectedIds.value = new Set();
  } finally {
    merging.value = false;
  }
}
</script>

<template>
  <div class="block-table-wrapper">
    <div v-if="selectedCount >= 2" class="merge-bar">
      <span>{{ selectedCount }} bloques seleccionados</span>
      <button class="btn btn-merge" @click="mergeSelected" :disabled="merging">
        <GitMerge :size="14" :stroke-width="2" />
        {{ merging ? 'Fusionando...' : 'Fusionar seleccionados' }}
      </button>
      <button class="btn btn-ghost-sm" @click="selectedIds = new Set()">Cancelar</button>
    </div>
    <table class="block-table">
      <thead>
        <tr>
          <th class="col-select">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate="selectedCount > 0 && !allSelected"
              @change="toggleAll"
              title="Seleccionar todos"
            />
          </th>
          <th :style="colStyle('time')" class="sortable resizable" @click="toggleSort('start_time')">
            Inicio{{ sortIcon('start_time') }}
            <span class="resize-handle" @mousedown.stop="startResize('time', $event)"></span>
          </th>
          <th :style="colStyle('time')" class="sortable resizable" @click="toggleSort('end_time')">
            Fin{{ sortIcon('end_time') }}
            <span class="resize-handle" @mousedown.stop="startResize('time', $event)"></span>
          </th>
          <th :style="colStyle('duration')" class="sortable resizable" @click="toggleSort('duration_minutes')">
            Duracion{{ sortIcon('duration_minutes') }}
            <span class="resize-handle" @mousedown.stop="startResize('duration', $event)"></span>
          </th>
          <th :style="colStyle('app')" class="sortable resizable" @click="toggleSort('app_name')">
            App / Contexto{{ sortIcon('app_name') }}
            <span class="resize-handle" @mousedown.stop="startResize('app', $event)"></span>
          </th>
          <th :style="colStyle('description')" class="resizable">
            Descripcion
            <span class="resize-handle" @mousedown.stop="startResize('description', $event)"></span>
          </th>
          <th :style="colStyle('project')" class="sortable resizable" @click="toggleSort('odoo_project_name')">
            Proyecto{{ sortIcon('odoo_project_name') }}
            <span class="resize-handle" @mousedown.stop="startResize('project', $event)"></span>
          </th>
          <th :style="colStyle('task')" class="resizable">
            Tarea
            <span class="resize-handle" @mousedown.stop="startResize('task', $event)"></span>
          </th>
          <th :style="colStyle('status')" class="sortable" @click="toggleSort('status')">Estado{{ sortIcon('status') }}</th>
          <th :style="colStyle('actions')">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <BlockRow
          v-for="block in sorted"
          :key="block.id"
          :block="block"
          :selected="selectedIds.has(block.id)"
          :selectable="block.status !== 'synced'"
          @toggle-select="toggleSelect(block.id)"
        />
      </tbody>
    </table>

    <EmptyState v-if="blocks.length === 0" text="Sin bloques para esta fecha" />
  </div>
</template>

<style scoped>
.block-table-wrapper { overflow-x: auto; }

.block-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.block-table th {
  text-align: left;
  padding: 10px 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  position: relative;
  overflow: hidden;
  text-overflow: ellipsis;
}

.resizable { position: relative; }

.resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
}

.resize-handle:hover,
.resize-handle:active {
  background: var(--accent);
}

.col-select {
  width: 32px;
  text-align: center;
  padding: 10px 4px;
}

.col-select input[type="checkbox"] {
  cursor: pointer;
  accent-color: var(--accent);
}

.merge-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
  background: var(--accent-soft);
  border: 1px solid var(--accent);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.btn-merge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.btn-merge:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-merge:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost-sm {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.btn-ghost-sm:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
</style>
