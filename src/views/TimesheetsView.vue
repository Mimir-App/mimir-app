<script setup lang="ts">
import { onMounted, watch, ref } from 'vue';
import { useTimesheetsStore } from '../stores/timesheets';
import type { TimesheetEntry } from '../lib/types';
import { formatHours, formatDate } from '../composables/useFormatting';
import { useColumnWidths } from '../composables/useColumnWidths';
import { provideCollapseAll } from '../composables/useCollapseAll';
import ViewToolbar from '../components/shared/ViewToolbar.vue';
import CustomSelect from '../components/shared/CustomSelect.vue';
import CustomDatePicker from '../components/shared/CustomDatePicker.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import StatusBanner from '../components/shared/StatusBanner.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import EmptyState from '../components/shared/EmptyState.vue';

const tsStore = useTimesheetsStore();
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
const { colStyle, startResize } = useColumnWidths();

onMounted(() => { tsStore.fetchEntries(); });
watch([() => tsStore.dateFrom, () => tsStore.dateTo], () => { tsStore.fetchEntries(); });

type SortDir = 'asc' | 'desc';
const sortKey = ref('date');
const sortDir = ref<SortDir>('asc');

function toggleSort(key: string) {
  if (sortKey.value === key) { sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'; }
  else { sortKey.value = key; sortDir.value = 'asc'; }
}

function sortIcon(key: string): string {
  if (sortKey.value !== key) return '';
  return sortDir.value === 'asc' ? ' \u25B2' : ' \u25BC';
}

function sortEntries(entries: TimesheetEntry[]): TimesheetEntry[] {
  const key = sortKey.value;
  const dir = sortDir.value === 'asc' ? 1 : -1;
  return [...entries].sort((a, b) => {
    const va = (a as unknown as Record<string, unknown>)[key];
    const vb = (b as unknown as Record<string, unknown>)[key];
    if (va == null && vb == null) return 0;
    if (va == null) return dir;
    if (vb == null) return -dir;
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
    return String(va).localeCompare(String(vb)) * dir;
  });
}

const dummyFilter = ref('');
</script>

<template>
  <div class="timesheets-view">
    <ViewToolbar
      v-model:filter="dummyFilter"
      :showFilter="false"
      showCollapse
      :allExpanded="allExpanded"
      :showRefresh="false"
      @toggleCollapse="toggleCollapseAll"
    >
      <label class="toolbar-field">
        Desde
        <CustomDatePicker v-model="tsStore.dateFrom" />
      </label>
      <label class="toolbar-field">
        Hasta
        <CustomDatePicker v-model="tsStore.dateTo" />
      </label>
      <CustomSelect v-model="tsStore.groupBy" :options="[
        { value: 'date', label: 'Fecha' },
        { value: 'week', label: 'Semana' },
        { value: 'project', label: 'Proyecto' },
        { value: 'task', label: 'Tarea' },
      ]" />
      <span class="total-hours">
        Total: <strong>{{ formatHours(tsStore.totalHours) }}</strong>
      </span>
    </ViewToolbar>

    <StatusBanner v-if="tsStore.error" type="error">{{ tsStore.error }}</StatusBanner>
    <LoadingState v-if="tsStore.loading" text="Cargando timesheets..." />

    <template v-else>
      <CollapsibleGroup
        v-for="(group, key) in tsStore.grouped"
        :key="key"
        :label="tsStore.groupBy === 'date' ? formatDate(group.label) : group.label"
        :count="group.entries.length"
        :summary="formatHours(group.hours)"
      >
        <table class="ts-table">
          <thead>
            <tr>
              <th v-if="tsStore.groupBy !== 'date'" :style="colStyle('date')" class="sortable resizable" @click="toggleSort('date')">
                Fecha{{ sortIcon('date') }}<span class="resize-handle" @mousedown.stop="startResize('date', $event)"></span>
              </th>
              <th v-if="tsStore.groupBy !== 'project'" :style="colStyle('project')" class="sortable resizable" @click="toggleSort('project_name')">
                Proyecto{{ sortIcon('project_name') }}<span class="resize-handle" @mousedown.stop="startResize('project', $event)"></span>
              </th>
              <th :style="colStyle('task')" class="sortable resizable" @click="toggleSort('task_name')">
                Tarea{{ sortIcon('task_name') }}<span class="resize-handle" @mousedown.stop="startResize('task', $event)"></span>
              </th>
              <th class="sortable col-expand" @click="toggleSort('description')">Descripcion{{ sortIcon('description') }}</th>
              <th :style="colStyle('hours')" class="sortable" @click="toggleSort('hours')">Horas{{ sortIcon('hours') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in sortEntries(group.entries)" :key="entry.id">
              <td v-if="tsStore.groupBy !== 'date'" :style="colStyle('date')">{{ formatDate(entry.date) }}</td>
              <td v-if="tsStore.groupBy !== 'project'" :style="colStyle('project')">{{ entry.project_name }}</td>
              <td :style="colStyle('task')">{{ entry.task_name ?? '—' }}</td>
              <td>{{ entry.description }}</td>
              <td :style="colStyle('hours')" class="col-hours">{{ formatHours(entry.hours) }}</td>
            </tr>
          </tbody>
        </table>
      </CollapsibleGroup>

      <EmptyState v-if="tsStore.entries.length === 0" text="Sin entradas de timesheet" />
    </template>
  </div>
</template>

<style scoped>
.toolbar-field {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.toolbar-field input {
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
  font-size: 13px;
  white-space: nowrap;
}

.total-hours strong {
  color: var(--accent);
}

.ts-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.ts-table th {
  text-align: left;
  padding: 10px 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  position: relative;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ts-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ts-table tr:hover td {
  background: var(--bg-hover);
}

.col-expand { width: auto; }

.col-hours {
  text-align: right;
}

.resizable { position: relative; }
.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent;
}
.resize-handle:hover, .resize-handle:active { background: var(--accent); }

</style>
