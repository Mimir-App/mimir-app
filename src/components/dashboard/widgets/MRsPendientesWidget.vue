<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useMergeRequestsStore } from '../../../stores/merge_requests';
import EmptyState from '../../shared/EmptyState.vue';

const props = defineProps<{ config: Record<string, any> }>();

const mrStore = useMergeRequestsStore();

const showOnlyConflicts = computed(() => props.config.show_only_conflicts ?? false);
const showOnlyFailed = computed(() => props.config.show_only_failed ?? false);

const filteredMRs = computed(() => {
  let result = mrStore.scoredMRs;
  if (showOnlyConflicts.value) {
    result = result.filter(mr => mr.has_conflicts);
  }
  if (showOnlyFailed.value) {
    result = result.filter(mr => mr.pipeline_status === 'failed');
  }
  return result.slice(0, 10);
});

onMounted(() => mrStore.fetchMergeRequests());
</script>

<template>
  <h3 class="card-title">MRs Pendientes</h3>
  <div class="mrs-list">
    <div v-for="mr in filteredMRs" :key="mr.id" class="mr-row">
      <span class="mr-score">{{ mr.score }}</span>
      <span class="mr-project">{{ mr.project_path }}</span>
      <span class="mr-title">{{ mr.title }}</span>
      <span v-if="mr.has_conflicts" class="mr-badge conflict">Conflictos</span>
      <span v-if="mr.pipeline_status === 'failed'" class="mr-badge failed">Pipeline</span>
    </div>
    <EmptyState v-if="filteredMRs.length === 0" text="Sin MRs pendientes" />
  </div>
</template>

<style scoped>
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.mrs-list { display: flex; flex-direction: column; gap: 6px; }
.mr-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px; font-size: 13px; }
.mr-row:hover { background: var(--bg-hover); }
.mr-score { min-width: 32px; text-align: right; font-weight: 600; color: var(--accent); }
.mr-project { color: var(--text-secondary); font-size: 12px; min-width: 150px; }
.mr-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mr-badge { font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: 600; }
.mr-badge.conflict { background: rgba(241, 76, 76, 0.15); color: var(--error); }
.mr-badge.failed { background: rgba(220, 220, 170, 0.15); color: var(--warning); }
</style>
