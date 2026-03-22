<script setup lang="ts">
import type { GitLabIssue, GitLabMergeRequest } from '../../lib/types';
import { formatDate } from '../../composables/useFormatting';
import SourceIcon from '../shared/SourceIcon.vue';

type DiscoverItem = (GitLabIssue | GitLabMergeRequest) & { _type?: string; _source?: string };

defineProps<{
  items: DiscoverItem[];
  followedKeys: Set<string>;
}>();

const emit = defineEmits<{
  select: [item: DiscoverItem];
  follow: [itemId: number];
  unfollow: [itemId: number];
  contextmenu: [item: DiscoverItem, event: MouseEvent];
}>();

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
        <th class="col-iid">#</th>
        <th class="col-title">Titulo</th>
        <th class="col-repo">Repositorio</th>
        <th class="col-labels">Labels</th>
        <th class="col-author">Autor</th>
        <th class="col-date">Fecha</th>
        <th class="col-action"></th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="item in items"
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
        <td class="col-iid muted">{{ item.iid }}</td>
        <td class="col-title">
          <span class="title-link">{{ item.title }}</span>
        </td>
        <td class="col-repo muted" :title="item.project_path">{{ item.project_path }}</td>
        <td class="col-labels">
          <span
            v-for="label in getLabels(item)"
            :key="label.name"
            class="label-tag"
            :style="labelStyle(label)"
          >{{ label.name }}</span>
        </td>
        <td class="col-author muted">{{ item.assignees?.[0]?.username ?? '' }}</td>
        <td class="col-date muted">{{ formatDate(item.updated_at) }}</td>
        <td class="col-action">
          <button
            v-if="followedKeys.has(`${item.project_path}#${item.iid}`)"
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
}

.data-table th {
  text-align: left;
  padding: 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.3px;
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
.col-iid { width: 45px; }
.col-title { }
.col-repo { width: 200px; font-size: 12px; }
.col-labels { width: 200px; }
.col-author { width: 100px; }
.col-date { width: 90px; }
.col-action { width: 80px; text-align: center; }

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
