<script setup lang="ts">
import type { GitLabMergeRequest } from '../../lib/types';
import ScoreBadge from '../shared/ScoreBadge.vue';

defineProps<{ mr: GitLabMergeRequest }>();
</script>

<template>
  <aside class="mr-detail">
    <div class="detail-header">
      <ScoreBadge :score="mr.score" />
      <h3>{{ mr.title }}</h3>
      <span class="mr-iid">!{{ mr.iid }}</span>
    </div>

    <div class="detail-meta">
      <div class="meta-row">
        <span class="meta-label">Estado</span>
        <span class="meta-value">{{ mr.state }}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Proyecto</span>
        <span class="meta-value">{{ mr.project_path }}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Rama</span>
        <span class="meta-value">{{ mr.source_branch }} → {{ mr.target_branch }}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Pipeline</span>
        <span class="meta-value" :class="mr.pipeline_status ? 'pipeline-' + mr.pipeline_status : ''">
          {{ mr.pipeline_status ?? '—' }}
        </span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Conflictos</span>
        <span class="meta-value" :class="mr.has_conflicts ? 'text-error' : ''">
          {{ mr.has_conflicts ? 'Sí' : 'No' }}
        </span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Labels</span>
        <div class="meta-value">
          <span v-for="l in mr.labels" :key="l" class="label-tag">{{ l }}</span>
        </div>
      </div>
      <div class="meta-row">
        <span class="meta-label">Asignados</span>
        <span class="meta-value">
          {{ mr.assignees.map(a => a.username).join(', ') || '—' }}
        </span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Reviewers</span>
        <span class="meta-value">
          {{ mr.reviewers.map(r => r.username).join(', ') || '—' }}
        </span>
      </div>
    </div>

    <div class="detail-description" v-if="mr.description">
      <h4>Descripción</h4>
      <p>{{ mr.description }}</p>
    </div>

    <a :href="mr.web_url" target="_blank" class="open-link">Abrir en GitLab</a>
  </aside>
</template>

<style scoped>
.mr-detail {
  width: 350px;
  padding: 16px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.detail-header { margin-bottom: 16px; }
.detail-header h3 { font-size: 15px; margin: 8px 0 4px; }
.mr-iid { font-size: 12px; color: var(--text-secondary); }

.detail-meta { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.meta-row { display: flex; justify-content: space-between; font-size: 13px; }
.meta-label { color: var(--text-secondary); }

.label-tag {
  display: inline-block;
  padding: 1px 6px;
  margin: 1px 2px;
  background: var(--bg-card);
  border-radius: 3px;
  font-size: 11px;
}

.pipeline-success { color: var(--success); }
.pipeline-failed { color: var(--error); }
.pipeline-running { color: var(--warning); }
.text-error { color: var(--error); }

.detail-description { margin-bottom: 16px; }
.detail-description h4 { font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }
.detail-description p { font-size: 13px; white-space: pre-wrap; word-break: break-word; }

.open-link { color: var(--accent); font-size: 13px; text-decoration: none; }
.open-link:hover { text-decoration: underline; }
</style>
