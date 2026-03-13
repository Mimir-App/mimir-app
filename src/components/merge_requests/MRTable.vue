<script setup lang="ts">
import type { GitLabMergeRequest } from '../../lib/types';
import ScoreBadge from '../shared/ScoreBadge.vue';

defineProps<{ mergeRequests: GitLabMergeRequest[] }>();
</script>

<template>
  <table class="mr-table">
    <thead>
      <tr>
        <th class="col-score">Score</th>
        <th class="col-iid">!</th>
        <th>Título</th>
        <th class="col-branch">Rama</th>
        <th class="col-pipeline">Pipeline</th>
        <th class="col-conflicts">Conflictos</th>
        <th class="col-date">Actualizado</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="mr in mergeRequests" :key="mr.id" class="mr-row">
        <td><ScoreBadge :score="mr.score" /></td>
        <td class="col-iid">{{ mr.iid }}</td>
        <td>
          <a :href="mr.web_url" target="_blank" class="mr-link">{{ mr.title }}</a>
        </td>
        <td class="col-branch">{{ mr.source_branch }}</td>
        <td class="col-pipeline">
          <span v-if="mr.pipeline_status" :class="'pipeline-' + mr.pipeline_status">
            {{ mr.pipeline_status }}
          </span>
          <span v-else class="no-pipeline">—</span>
        </td>
        <td class="col-conflicts">
          <span v-if="mr.has_conflicts" class="conflict-yes">Sí</span>
          <span v-else class="conflict-no">No</span>
        </td>
        <td class="col-date">{{ new Date(mr.updated_at).toLocaleDateString('es-ES') }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.mr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.mr-table th {
  text-align: left;
  padding: 6px 8px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}

.mr-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.mr-row:hover td {
  background: var(--bg-hover);
}

.col-score { width: 50px; }
.col-iid { width: 40px; color: var(--text-secondary); }
.col-branch { width: 150px; font-size: 12px; color: var(--text-secondary); }
.col-pipeline { width: 80px; }
.col-conflicts { width: 70px; }
.col-date { width: 90px; color: var(--text-secondary); font-size: 12px; }

.mr-link {
  color: var(--text-primary);
  text-decoration: none;
}

.mr-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.pipeline-success { color: var(--success); }
.pipeline-failed { color: var(--error); }
.pipeline-running { color: var(--warning); }
.pipeline-pending { color: var(--text-secondary); }
.no-pipeline { color: var(--text-secondary); }

.conflict-yes { color: var(--error); font-weight: 500; }
.conflict-no { color: var(--text-secondary); }
</style>
