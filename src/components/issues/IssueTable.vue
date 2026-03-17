<script setup lang="ts">
import { toRef } from 'vue';
import type { GitLabIssue } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import ScoreBadge from '../shared/ScoreBadge.vue';

const props = defineProps<{ issues: GitLabIssue[]; followedIds?: Set<number> }>();
const emit = defineEmits<{ select: [issue: GitLabIssue] }>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'issues'), 'score', 'desc');
const { colStyle, startResize } = useColumnWidths();
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th :style="colStyle('score')" class="sortable" @click="toggleSort('score')">Score{{ sortIcon('score') }}</th>
        <th :style="colStyle('iid')" class="sortable" @click="toggleSort('iid')">#{{ sortIcon('iid') }}</th>
        <th class="sortable col-expand resizable" @click="toggleSort('title')">
          Titulo{{ sortIcon('title') }}
          <span class="resize-handle" @mousedown.stop="startResize('description', $event)"></span>
        </th>
        <th :style="colStyle('labels')" class="resizable">
          Labels
          <span class="resize-handle" @mousedown.stop="startResize('labels', $event)"></span>
        </th>
        <th :style="colStyle('assignee')" class="resizable">
          Asignado
          <span class="resize-handle" @mousedown.stop="startResize('assignee', $event)"></span>
        </th>
        <th :style="colStyle('date')" class="sortable resizable" @click="toggleSort('updated_at')">
          Actualizado{{ sortIcon('updated_at') }}
          <span class="resize-handle" @mousedown.stop="startResize('date', $event)"></span>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="issue in sorted" :key="issue.id" class="data-row clickable-row" @click="emit('select', issue)">
        <td :style="colStyle('score')">
          <span class="score-cell">
            <span v-if="followedIds?.has(issue.id)" class="followed-dot" title="Seguida"></span>
            <ScoreBadge :score="issue.score" />
          </span>
        </td>
        <td :style="colStyle('iid')" class="muted">{{ issue.iid }}</td>
        <td class="col-expand">
          <a :href="issue.web_url" target="_blank" class="link" @click.stop>{{ issue.title }}</a>
        </td>
        <td :style="colStyle('labels')">
          <span v-for="label in issue.labels.slice(0, 3)" :key="label" class="label-tag">{{ label }}</span>
        </td>
        <td :style="colStyle('assignee')">
          <span v-for="a in issue.assignees" :key="a.id">{{ a.username }}</span>
        </td>
        <td :style="colStyle('date')" class="muted">{{ formatDate(issue.updated_at) }}</td>
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

.link { color: var(--text-primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; display: block; }
.link:hover { color: var(--accent); text-decoration: underline; }

.score-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.followed-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.label-tag {
  display: inline-block; padding: 1px 6px; margin-right: 4px;
  background: var(--bg-card); border-radius: 3px; font-size: 11px; color: var(--text-secondary); white-space: nowrap;
}

.resizable { position: relative; }
.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent;
}
.resize-handle:hover, .resize-handle:active { background: var(--accent); }
</style>
