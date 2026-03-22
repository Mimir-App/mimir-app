<script setup lang="ts">
import { toRef } from 'vue';
import type { GitLabMergeRequest } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import ScoreBadge from '../shared/ScoreBadge.vue';
import SourceIcon from '../shared/SourceIcon.vue';

const props = defineProps<{ mergeRequests: GitLabMergeRequest[]; followedIds?: Set<number> }>();
const emit = defineEmits<{
  select: [mr: GitLabMergeRequest];
  'update-score': [mrId: number, value: number];
  unfollow: [mrId: number];
  contextmenu: [mr: GitLabMergeRequest, event: MouseEvent];
}>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'mergeRequests'), 'score', 'desc');
const { colStyle, startResize } = useColumnWidths();
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th style="width: 24px; padding: 0 4px;"></th>
        <th style="width: 80px;" class="sortable" @click="toggleSort('score')">Score{{ sortIcon('score') }}</th>
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
      <tr v-for="mr in sorted" :key="mr.id" class="data-row clickable-row" @click="emit('select', mr)" @contextmenu.prevent="emit('contextmenu', mr, $event)">
        <td class="icon-cell">
          <SourceIcon :source="mr._source" :size="16" />
          <button v-if="followedIds?.has(mr.id)" class="followed-dot" title="Dejar de seguir" @click.stop="emit('unfollow', mr.id)"></button>
        </td>
        <td class="score-td">
          <ScoreBadge
            :score="mr.score"
            :manual-score="mr.manual_priority ?? 0"
            editable
            @update:manual-score="(v) => emit('update-score', mr.id, v)"
          />
        </td>
        <td :style="colStyle('iid')" class="muted">{{ mr.iid }}</td>
        <td class="col-expand">
          <a :href="mr.web_url" target="_blank" class="link" @click.stop>{{ mr.title }}</a>
        </td>
        <td :style="colStyle('branch')" class="muted truncate">{{ mr.source_branch }}</td>
        <td :style="colStyle('pipeline')">
          <span v-if="mr.pipeline_status" :class="'pipeline-' + mr.pipeline_status">{{ mr.pipeline_status }}</span>
          <span v-else class="muted">&mdash;</span>
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
.clickable-row { cursor: pointer; }
.col-expand { width: auto; }
.muted { color: var(--text-secondary); }
.truncate { overflow: hidden; text-overflow: ellipsis; }

.link { color: var(--text-primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; display: block; }
.link:hover { color: var(--accent); text-decoration: underline; }

.icon-cell {
  padding: 0 4px !important;
  text-align: center;
  position: relative;
}

.followed-dot {
  position: absolute;
  top: 2px;
  right: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  border: none;
  padding: 0;
  cursor: pointer;
}

.followed-dot:hover {
  background: var(--error);
}

.score-td {
  padding: 4px !important;
}

.score-td :deep(.score-badge),
.score-td :deep(.score-input) {
  width: 100%;
  min-width: unset;
  font-size: 14px;
  padding: 6px 8px;
}

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
