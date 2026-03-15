<script setup lang="ts">
import { toRef } from 'vue';
import type { ActivityBlock } from '../../lib/types';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import BlockRow from './BlockRow.vue';
import EmptyState from '../shared/EmptyState.vue';

const props = defineProps<{ blocks: ActivityBlock[] }>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'blocks'), 'start_time', 'asc');
const { colStyle, startResize } = useColumnWidths();
</script>

<template>
  <div class="block-table-wrapper">
    <table class="block-table">
      <thead>
        <tr>
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
        <BlockRow v-for="block in sorted" :key="block.id" :block="block" />
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
</style>
