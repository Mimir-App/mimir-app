<script setup lang="ts">
import { toRef } from 'vue';
import type { GitLabIssue, GitLabMergeRequest } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import { useSortable } from '../../composables/useSortable';
import { useColumnWidths } from '../../composables/useColumnWidths';
import SourceIcon from '../shared/SourceIcon.vue';

type DiscoverItem = (GitLabIssue | GitLabMergeRequest) & { _type?: string; _source?: string };

const props = defineProps<{
  items: DiscoverItem[];
  followedKeys?: Set<string>;
}>();

const emit = defineEmits<{
  select: [item: DiscoverItem];
  follow: [itemId: number];
  unfollow: [itemId: number];
  contextmenu: [item: DiscoverItem, event: MouseEvent];
}>();

const { toggleSort, sortIcon, sorted } = useSortable(toRef(props, 'items'), 'updated_at', 'desc');
const { colStyle, startResize } = useColumnWidths();

function typeLabel(item: DiscoverItem): string {
  return item._type === 'merge_request' ? 'PR' : 'Issue';
}

function getLabels(item: DiscoverItem) {
  if ('label_objects' in item && item.label_objects?.length) return item.label_objects.slice(0, 3);
  const labels = ('labels' in item && item.labels) ? item.labels : [];
  return labels.slice(0, 3).map((l: string) => ({ name: l, color: '' }));
}

function labelStyle(label: { name: string; color: string }) {
  if (!label.color) return {};
  return {
    background: label.color + '22',
    color: label.color,
    border: `1px solid ${label.color}55`,
  };
}
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th class="col-icon"></th>
        <th class="col-type">Tipo</th>
        <th :style="colStyle('iid')" class="sortable" @click="toggleSort('iid')">#{{ sortIcon('iid') }}</th>
        <th class="sortable col-title" @click="toggleSort('title')">Titulo{{ sortIcon('title') }}</th>
        <th :style="colStyle('discover-repo')" class="resizable">
          Repositorio
          <span class="resize-handle" @mousedown.stop="startResize('discover-repo', $event)"></span>
        </th>
        <th :style="colStyle('labels')" class="resizable">
          Labels
          <span class="resize-handle" @mousedown.stop="startResize('labels', $event)"></span>
        </th>
        <th :style="colStyle('assignee')" class="resizable">
          Autor
          <span class="resize-handle" @mousedown.stop="startResize('assignee', $event)"></span>
        </th>
        <th :style="colStyle('date')" class="sortable resizable" @click="toggleSort('updated_at')">
          Fecha{{ sortIcon('updated_at') }}
          <span class="resize-handle" @mousedown.stop="startResize('date', $event)"></span>
        </th>
        <th class="col-action"></th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="item in sorted"
        :key="item.id"
        class="data-row clickable-row"
        @click="emit('select', item)"
        @contextmenu.prevent="emit('contextmenu', item, $event)"
      >
        <td class="col-icon">
          <SourceIcon :source="item._source" :size="16" />
        </td>
        <td class="col-type">
          <span class="type-badge" :class="item._type === 'merge_request' ? 'type-pr' : 'type-issue'">
            {{ typeLabel(item) }}
          </span>
        </td>
        <td :style="colStyle('iid')" class="muted">{{ item.iid }}</td>
        <td class="col-title">
          <span class="title-link">{{ item.title }}</span>
        </td>
        <td :style="colStyle('discover-repo')" class="muted" :title="item.project_path">{{ item.project_path }}</td>
        <td :style="colStyle('labels')">
          <span
            v-for="label in getLabels(item)"
            :key="label.name"
            class="label-tag"
            :style="labelStyle(label)"
          >{{ label.name }}</span>
        </td>
        <td :style="colStyle('assignee')" class="muted">{{ item.assignees?.[0]?.username ?? '' }}</td>
        <td :style="colStyle('date')" class="muted">{{ formatDate(item.updated_at) }}</td>
        <td class="col-action">
          <button
            v-if="(followedKeys ?? new Set()).has(`${item.project_path}#${item.iid}`)"
            class="btn-following"
            @click.stop="emit('unfollow', item.id)"
          >Siguiendo</button>
          <button
            v-else
            class="btn-follow"
            @click.stop="emit('follow', item.id)"
          >Seguir</button>
        </td>
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
.muted { color: var(--text-secondary); }

/* Column widths */
.col-icon { width: 28px; text-align: center; }
.col-type { width: 50px; }
.col-title { width: auto; }
.col-action { width: 80px; text-align: center; }

/* Resizable columns */
.resizable { position: relative; }
.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent;
}
.resize-handle:hover, .resize-handle:active { background: var(--accent); }

/* Type badge */
.type-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.type-issue {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
}

.type-pr {
  background: rgba(86, 156, 214, 0.15);
  color: #569cd6;
}

/* Title */
.title-link {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.title-link:hover { color: var(--accent); }

/* Labels */
.label-tag {
  display: inline-block;
  padding: 1px 6px;
  margin-right: 3px;
  background: var(--bg-card);
  border: 1px solid transparent;
  border-radius: 3px;
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Action buttons */
.btn-follow, .btn-following {
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid;
}

.btn-follow {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.btn-follow:hover {
  background: var(--accent-hover);
}

.btn-following {
  background: transparent;
  color: var(--success);
  border-color: var(--success);
}

.btn-following:hover {
  color: var(--error);
  border-color: var(--error);
}
</style>
