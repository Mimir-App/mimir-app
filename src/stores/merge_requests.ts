import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabMergeRequest } from '../lib/types';
import { computeMRScore, sortByScore, groupByProject } from '../lib/scoring';
import { api } from '../lib/api';

export type MRGroupBy = 'project' | 'priority' | 'none';

const PRIORITY_ORDER = ['priority::critical', 'priority::high', 'priority::medium', 'priority::low'];

function getPriorityLabel(labels: string[]): string {
  for (const p of PRIORITY_ORDER) {
    if (labels.includes(p)) return p.replace('priority::', '').toUpperCase();
  }
  return 'Sin prioridad';
}

export const useMergeRequestsStore = defineStore('merge_requests', () => {
  const mergeRequests = ref<GitLabMergeRequest[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filterText = ref('');
  const groupBy = ref<MRGroupBy>('project');

  const scoredMRs = computed(() => {
    const scored = mergeRequests.value.map(mr => ({
      ...mr,
      score: computeMRScore(mr),
    }));
    return sortByScore(scored);
  });

  const filteredMRs = computed(() => {
    if (!filterText.value) return scoredMRs.value;
    const q = filterText.value.toLowerCase();
    return scoredMRs.value.filter(
      mr =>
        mr.title.toLowerCase().includes(q) ||
        mr.project_path.toLowerCase().includes(q) ||
        mr.source_branch.toLowerCase().includes(q)
    );
  });

  const groupedByProject = computed(() => groupByProject(filteredMRs.value));

  const groupedByPriority = computed(() => {
    const groups: Record<string, (typeof filteredMRs.value)> = {};
    for (const mr of filteredMRs.value) {
      const key = getPriorityLabel(mr.labels);
      if (!groups[key]) groups[key] = [];
      groups[key].push(mr);
    }
    const sorted: Record<string, typeof filteredMRs.value> = {};
    for (const label of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'Sin prioridad']) {
      if (groups[label]) sorted[label] = groups[label];
    }
    return sorted;
  });

  const groupedMRs = computed(() => {
    switch (groupBy.value) {
      case 'priority': return groupedByPriority.value;
      case 'none': return { 'Todas las MRs': filteredMRs.value } as Record<string, GitLabMergeRequest[]>;
      default: return groupedByProject.value;
    }
  });

  async function fetchMergeRequests() {
    loading.value = true;
    error.value = null;
    try {
      mergeRequests.value = await api.getMergeRequests() as GitLabMergeRequest[];
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  return {
    mergeRequests,
    loading,
    error,
    filterText,
    groupBy,
    scoredMRs,
    filteredMRs,
    groupedMRs,
    fetchMergeRequests,
  };
});
