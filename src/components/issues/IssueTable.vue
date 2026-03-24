<script setup lang="ts">
import { toRef } from 'vue';
import type { GitLabIssue } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import ScoreBadge from '../shared/ScoreBadge.vue';
import SourceIcon from '../shared/SourceIcon.vue';

const props = defineProps<{
  issues: GitLabIssue[];
  followedKeys?: Set<string>;
}>();
const emit = defineEmits<{
  select: [issue: GitLabIssue];
  'update-score': [issueId: number, value: number];
  unfollow: [issueId: number];
  contextmenu: [issue: GitLabIssue, event: MouseEvent];
}>();
const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'issues'), 'score', 'desc');
const { colStyle, startResize } = useColumnWidths();

function labelStyle(label: { name: string; color: string }) {
  if (!label.color) return {};
  return {
    background: label.color + '22',
    color: label.color,
    border: `1px solid ${label.color}55`,
  };
}

function getLabels(issue: GitLabIssue) {
  if (issue.label_objects?.length) return issue.label_objects.slice(0, 3);
  return issue.labels.slice(0, 3).map(l => ({ name: l, color: '' }));
}
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th style="width: 24px; padding: 0 4px;"></th>
        <th style="width: 80px;" class="sortable" @click="toggleSort('score')">Score{{ sortIcon('score') }}</th>
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
      <tr v-for="issue in sorted" :key="issue.id" class="data-row clickable-row" @click="emit('select', issue)" @contextmenu.prevent="emit('contextmenu', issue, $event)">
        <td class="icon-cell">
          <SourceIcon :source="issue._source" :size="16" />
          <button
            v-if="followedKeys?.has(`${issue.project_path}#${issue.iid}`)"
            class="followed-dot"
            title="Dejar de seguir"
            @click.stop="emit('unfollow', issue.id)"
          ></button>
        </td>
        <td class="score-td">
          <ScoreBadge
            :score="issue.score"
            :manual-score="issue.manual_priority ?? 0"
            editable
            @update:manual-score="(v) => emit('update-score', issue.id, v)"
          />
        </td>
        <td :style="colStyle('iid')" class="muted">{{ issue.iid }}</td>
        <td class="col-expand">
          <span class="link">{{ issue.title }}</span>
        </td>
        <td :style="colStyle('labels')">
          <span
            v-for="label in getLabels(issue)"
            :key="label.name"
            class="label-tag"
            :style="labelStyle(label)"
          >{{ label.name }}</span>
        </td>
        <td :style="colStyle('assignee')">
          <span v-for="a in issue.assignees" :key="a.id || a.username">{{ a.username }}</span>
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
  font-size: var(--text-xs);
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

.label-tag {
  display: inline-block;
  padding: 1px 6px;
  margin-right: 4px;
  background: var(--bg-card);
  border: 1px solid transparent;
  border-radius: 3px;
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.resizable { position: relative; }
.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent;
}
.resize-handle:hover, .resize-handle:active { background: var(--accent); }
</style>
