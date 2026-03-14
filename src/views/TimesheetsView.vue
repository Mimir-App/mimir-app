<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { useTimesheetsStore } from '../stores/timesheets';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';

const tsStore = useTimesheetsStore();

onMounted(() => {
  tsStore.fetchEntries();
});

watch([() => tsStore.dateFrom, () => tsStore.dateTo], () => {
  tsStore.fetchEntries();
});
</script>

<template>
  <div class="timesheets-view">
    <div class="ts-toolbar">
      <label>
        Desde
        <input type="date" v-model="tsStore.dateFrom" class="date-picker" />
      </label>
      <label>
        Hasta
        <input type="date" v-model="tsStore.dateTo" class="date-picker" />
      </label>
      <label>
        Agrupar por
        <select v-model="tsStore.groupBy" class="group-select">
          <option value="date">Fecha</option>
          <option value="project">Proyecto</option>
        </select>
      </label>
      <span class="total-hours">
        Total: <strong>{{ tsStore.totalHours.toFixed(1) }}h</strong>
      </span>
    </div>

    <div v-if="tsStore.error" class="error-banner">{{ tsStore.error }}</div>
    <div v-if="tsStore.loading" class="loading">Cargando timesheets...</div>

    <template v-else>
      <CollapsibleGroup
        v-for="(group, key) in tsStore.grouped"
        :key="key"
        :label="group.label"
        :count="group.entries.length"
        :summary="group.hours.toFixed(1) + 'h'"
      >
        <table class="ts-table">
          <thead>
            <tr>
              <th v-if="tsStore.groupBy !== 'date'">Fecha</th>
              <th v-if="tsStore.groupBy !== 'project'">Proyecto</th>
              <th>Tarea</th>
              <th>Descripcion</th>
              <th class="col-hours">Horas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in group.entries" :key="entry.id">
              <td v-if="tsStore.groupBy !== 'date'">{{ entry.date }}</td>
              <td v-if="tsStore.groupBy !== 'project'">{{ entry.project_name }}</td>
              <td>{{ entry.task_name ?? '—' }}</td>
              <td>{{ entry.description }}</td>
              <td class="col-hours">{{ entry.hours.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </CollapsibleGroup>

      <div v-if="tsStore.entries.length === 0" class="empty-state">
        Sin entradas de timesheet
      </div>
    </template>
  </div>
</template>

<style scoped>
.ts-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
}

.ts-toolbar label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.date-picker,
.group-select {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
}

.total-hours {
  margin-left: auto;
  color: var(--text-secondary);
}

.total-hours strong {
  color: var(--accent);
}

.ts-group {
  margin-bottom: 20px;
}

.group-header {
  font-size: 14px;
  font-weight: 600;
  padding: 8px 0;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
  display: flex;
  justify-content: space-between;
}

.group-hours {
  color: var(--accent);
  font-weight: 500;
}

.ts-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ts-table th {
  text-align: left;
  padding: 6px 8px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}

.ts-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.ts-table tr:hover td {
  background: var(--bg-hover);
}

.col-hours {
  text-align: right;
  min-width: 60px;
}

.error-banner {
  padding: 10px 14px;
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  border-radius: 4px;
  color: var(--error);
  font-size: 13px;
  margin-bottom: 12px;
}

.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
