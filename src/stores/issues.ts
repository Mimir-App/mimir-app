import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabIssue } from '../lib/types';
import { computeIssueScore, sortByScore, groupByProject } from '../lib/scoring';

export const useIssuesStore = defineStore('issues', () => {
  const issues = ref<GitLabIssue[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filterText = ref('');

  const scoredIssues = computed(() => {
    const scored = issues.value.map(issue => ({
      ...issue,
      score: computeIssueScore(issue),
    }));
    return sortByScore(scored);
  });

  const filteredIssues = computed(() => {
    if (!filterText.value) return scoredIssues.value;
    const q = filterText.value.toLowerCase();
    return scoredIssues.value.filter(
      i =>
        i.title.toLowerCase().includes(q) ||
        i.project_path.toLowerCase().includes(q) ||
        i.labels.some(l => l.toLowerCase().includes(q))
    );
  });

  const groupedIssues = computed(() => groupByProject(filteredIssues.value));

  async function fetchIssues() {
    loading.value = true;
    error.value = null;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      issues.value = await invoke<GitLabIssue[]>('get_issues');
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  return {
    issues,
    loading,
    error,
    filterText,
    scoredIssues,
    filteredIssues,
    groupedIssues,
    fetchIssues,
  };
});
