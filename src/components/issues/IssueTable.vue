<script setup lang="ts">
import type { GitLabIssue } from '../../lib/types';
import ScoreBadge from '../shared/ScoreBadge.vue';

defineProps<{ issues: GitLabIssue[] }>();
</script>

<template>
  <table class="issue-table">
    <thead>
      <tr>
        <th class="col-score">Score</th>
        <th class="col-iid">#</th>
        <th>Título</th>
        <th class="col-labels">Labels</th>
        <th class="col-assignee">Asignado</th>
        <th class="col-date">Actualizado</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="issue in issues" :key="issue.id" class="issue-row">
        <td><ScoreBadge :score="issue.score" /></td>
        <td class="col-iid">{{ issue.iid }}</td>
        <td>
          <a :href="issue.web_url" target="_blank" class="issue-link">
            {{ issue.title }}
          </a>
        </td>
        <td class="col-labels">
          <span v-for="label in issue.labels.slice(0, 3)" :key="label" class="label-tag">
            {{ label }}
          </span>
        </td>
        <td class="col-assignee">
          <span v-for="a in issue.assignees" :key="a.id">{{ a.username }}</span>
        </td>
        <td class="col-date">{{ new Date(issue.updated_at).toLocaleDateString('es-ES') }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.issue-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.issue-table th {
  text-align: left;
  padding: 6px 8px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}

.issue-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.issue-row:hover td {
  background: var(--bg-hover);
}

.col-score { width: 50px; }
.col-iid { width: 40px; color: var(--text-secondary); }
.col-labels { width: 200px; }
.col-assignee { width: 100px; }
.col-date { width: 90px; color: var(--text-secondary); font-size: 12px; }

.issue-link {
  color: var(--text-primary);
  text-decoration: none;
}

.issue-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.label-tag {
  display: inline-block;
  padding: 1px 6px;
  margin-right: 4px;
  background: var(--bg-card);
  border-radius: 3px;
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
