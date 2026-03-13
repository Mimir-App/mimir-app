<script setup lang="ts">
import type { GitLabIssue } from '../../lib/types';
import ScoreBadge from '../shared/ScoreBadge.vue';

defineProps<{ issue: GitLabIssue }>();
</script>

<template>
  <aside class="issue-detail">
    <div class="detail-header">
      <ScoreBadge :score="issue.score" />
      <h3>{{ issue.title }}</h3>
      <span class="issue-iid">#{{ issue.iid }}</span>
    </div>

    <div class="detail-meta">
      <div class="meta-row">
        <span class="meta-label">Estado</span>
        <span class="meta-value">{{ issue.state }}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Proyecto</span>
        <span class="meta-value">{{ issue.project_path }}</span>
      </div>
      <div class="meta-row" v-if="issue.milestone">
        <span class="meta-label">Milestone</span>
        <span class="meta-value">{{ issue.milestone }}</span>
      </div>
      <div class="meta-row" v-if="issue.due_date">
        <span class="meta-label">Fecha límite</span>
        <span class="meta-value">{{ issue.due_date }}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Labels</span>
        <div class="meta-value">
          <span v-for="l in issue.labels" :key="l" class="label-tag">{{ l }}</span>
        </div>
      </div>
      <div class="meta-row">
        <span class="meta-label">Asignados</span>
        <span class="meta-value">
          {{ issue.assignees.map(a => a.username).join(', ') || '—' }}
        </span>
      </div>
    </div>

    <div class="detail-description" v-if="issue.description">
      <h4>Descripción</h4>
      <p>{{ issue.description }}</p>
    </div>

    <a :href="issue.web_url" target="_blank" class="open-link">Abrir en GitLab</a>
  </aside>
</template>

<style scoped>
.issue-detail {
  width: 350px;
  padding: 16px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-header h3 {
  font-size: 15px;
  margin: 8px 0 4px;
}

.issue-iid {
  font-size: 12px;
  color: var(--text-secondary);
}

.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.meta-label {
  color: var(--text-secondary);
}

.label-tag {
  display: inline-block;
  padding: 1px 6px;
  margin: 1px 2px;
  background: var(--bg-card);
  border-radius: 3px;
  font-size: 11px;
}

.detail-description {
  margin-bottom: 16px;
}

.detail-description h4 {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.detail-description p {
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.open-link {
  display: inline-block;
  color: var(--accent);
  font-size: 13px;
  text-decoration: none;
}

.open-link:hover {
  text-decoration: underline;
}
</style>
