import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabMergeRequest } from '../lib/types';
import { computeMRScore, sortByScore, groupByProject } from '../lib/scoring';
import { api } from '../lib/api';

export const useMergeRequestsStore = defineStore('merge_requests', () => {
  const mergeRequests = ref<GitLabMergeRequest[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filterText = ref('');

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

  const groupedMRs = computed(() => groupByProject(filteredMRs.value));

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
    scoredMRs,
    filteredMRs,
    groupedMRs,
    fetchMergeRequests,
  };
});
