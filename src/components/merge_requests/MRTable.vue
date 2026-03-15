<script setup lang="ts">
import { toRef } from 'vue';
import type { GitLabMergeRequest } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import ScoreBadge from '../shared/ScoreBadge.vue';

const props = defineProps<{ mergeRequests: GitLabMergeRequest[] }>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'mergeRequests'), 'score', 'desc');
const { colStyle, startResize } = useColumnWidths();
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th :style="colStyle('score')" class="sortable" @click="toggleSort('score')">Score{{ sortIcon('score') }}</th>
        <th :style="colStyle('iid')" class="sortable" @click="toggleSort('iid')">!{{ sortIcon('iid') }}</th>
        <th class="sortable col-expand resizable" @click="toggleSort('title')">
          Titulo{{ sortIcon('title') }}
          <span class="resize-handle" @mousedown.stop="startResize('description', $event)"></span>
        </th>
        <th :style="colStyle('branch')" class="sortable resizable" @click="toggleSort('source_branch')">
          Rama{{ sortIcon('source_branch') }}
          <span class="resize-handle" @mousedown.stop="startResize('branch', $event)"></span>
        </th>
        <th :style="colStyle('pipeline')" class="sortable" @click="toggleSort('pipeline_status')">Pipeline{{ sortIcon('pipeline_status') }}</th>
        <th :style="colStyle('conflicts')" class="sortable" @click="toggleSort('has_conflicts')">Conflictos{{ sortIcon('has_conflicts') }}</th>
        <th :style="colStyle('date')" class="sortable resizable" @click="toggleSort('updated_at')">
          Actualizado{{ sortIcon('updated_at') }}
          <span class="resize-handle" @mousedown.stop="startResize('date', $event)"></span>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="mr in sorted" :key="mr.id" class="data-row">
        <td :style="colStyle('score')"><ScoreBadge :score="mr.score" /></td>
        <td :style="colStyle('iid')" class="muted">{{ mr.iid }}</td>
        <td class="col-expand">
          <a :href="mr.web_url" target="_blank" class="link">{{ mr.title }}</a>
        </td>
        <td :style="colStyle('branch')" class="muted truncate">{{ mr.source_branch }}</td>
        <td :style="colStyle('pipeline')">
          <span v-if="mr.pipeline_status" :class="'pipeline-' + mr.pipeline_status">{{ mr.pipeline_status }}</span>
          <span v-else class="muted">—</span>
        </td>
        <td :style="colStyle('conflicts')">
          <span v-if="mr.has_conflicts" class="conflict-yes">Si</span>
          <span v-else class="muted">No</span>
        </td>
        <td :style="colStyle('date')" class="muted">{{ formatDate(mr.updated_at) }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.data-table th {
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

.data-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-row:hover td { background: var(--bg-hover); }
.col-expand { width: auto; }
.muted { color: var(--text-secondary); }
.truncate { overflow: hidden; text-overflow: ellipsis; }

.link { color: var(--text-primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; display: block; }
.link:hover { color: var(--accent); text-decoration: underline; }

.pipeline-success { color: var(--success); }
.pipeline-failed { color: var(--error); }
.pipeline-running { color: var(--warning); }
.pipeline-pending { color: var(--text-secondary); }
.conflict-yes { color: var(--error); font-weight: 500; }

.resizable { position: relative; }
.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent;
}
.resize-handle:hover, .resize-handle:active { background: var(--accent); }
</style>
