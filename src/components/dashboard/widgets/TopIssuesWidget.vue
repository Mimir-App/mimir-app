<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useIssuesStore } from '../../../stores/issues';
import EmptyState from '../../shared/EmptyState.vue';

const props = defineProps<{ config: Record<string, any> }>();

const issuesStore = useIssuesStore();

const count = computed(() => props.config.count ?? 5);
const topIssues = computed(() => issuesStore.scoredIssues.slice(0, count.value));

onMounted(() => issuesStore.fetchIssues());
</script>

<template>
  <h3 class="card-title">Top Issues por Score</h3>
  <div class="top-issues">
    <div v-for="issue in topIssues" :key="issue.id" class="issue-row">
      <span class="issue-score">{{ issue.score }}</span>
      <span class="issue-project">{{ issue.project_path }}</span>
      <span class="issue-title">{{ issue.title }}</span>
    </div>
    <EmptyState v-if="issuesStore.scoredIssues.length === 0" text="Sin issues cargadas" />
  </div>
</template>

<style scoped>
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.top-issues { display: flex; flex-direction: column; gap: 6px; }
.issue-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px; font-size: 13px; }
.issue-row:hover { background: var(--bg-hover); }
.issue-score { min-width: 32px; text-align: right; font-weight: 600; color: var(--accent); }
.issue-project { color: var(--text-secondary); font-size: 12px; min-width: 150px; }
.issue-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
