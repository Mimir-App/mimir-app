<script setup lang="ts">
import type { ActivityBlock } from '../../lib/types';
import BlockRow from './BlockRow.vue';

defineProps<{ blocks: ActivityBlock[] }>();
</script>

<template>
  <div class="block-table-wrapper">
    <table class="block-table">
      <thead>
        <tr>
          <th class="col-time">Inicio</th>
          <th class="col-time">Fin</th>
          <th class="col-duration">Duración</th>
          <th class="col-app">App / Contexto</th>
          <th class="col-desc">Descripción</th>
          <th class="col-project">Proyecto</th>
          <th class="col-task">Tarea</th>
          <th class="col-status">Estado</th>
          <th class="col-actions">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <BlockRow v-for="block in blocks" :key="block.id" :block="block" />
      </tbody>
    </table>

    <div v-if="blocks.length === 0" class="empty-state">
      Sin bloques para esta fecha
    </div>
  </div>
</template>

<style scoped>
.block-table-wrapper {
  overflow-x: auto;
}

.block-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.block-table th {
  text-align: left;
  padding: 8px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12px;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}

.col-time { width: 70px; }
.col-duration { width: 60px; }
.col-app { width: 140px; }
.col-desc { min-width: 200px; }
.col-project { width: 160px; }
.col-task { width: 160px; }
.col-status { width: 80px; }
.col-actions { width: 60px; }

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
