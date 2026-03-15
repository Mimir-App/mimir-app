import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabIssue } from '../lib/types';
import { computeIssueScore, sortByScore, groupByProject } from '../lib/scoring';
import { api } from '../lib/api';

export type IssueGroupBy = 'project' | 'priority' | 'none';

const PRIORITY_ORDER = ['priority::critical', 'priority::high', 'priority::medium', 'priority::low'];

function getPriorityLabel(labels: string[]): string {
  for (const p of PRIORITY_ORDER) {
    if (labels.includes(p)) return p.replace('priority::', '').toUpperCase();
  }
  return 'Sin prioridad';
}

export const useIssuesStore = defineStore('issues', () => {
  const issues = ref<GitLabIssue[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filterText = ref('');
  const groupBy = ref<IssueGroupBy>('project');

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

  const groupedByProject = computed(() => groupByProject(filteredIssues.value));

  const groupedByPriority = computed(() => {
    const groups: Record<string, (typeof filteredIssues.value)> = {};
    for (const issue of filteredIssues.value) {
      const key = getPriorityLabel(issue.labels);
      if (!groups[key]) groups[key] = [];
      groups[key].push(issue);
    }
    // Ordenar por prioridad
    const sorted: Record<string, typeof filteredIssues.value> = {};
    for (const label of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'Sin prioridad']) {
      if (groups[label]) sorted[label] = groups[label];
    }
    return sorted;
  });

  const groupedIssues = computed(() => {
    switch (groupBy.value) {
      case 'priority': return groupedByPriority.value;
      case 'none': return { 'Todas las issues': filteredIssues.value } as Record<string, GitLabIssue[]>;
      default: return groupedByProject.value;
    }
  });

  async function fetchIssues() {
    loading.value = true;
    error.value = null;
    try {
      issues.value = await api.getIssues() as GitLabIssue[];
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
    groupBy,
    scoredIssues,
    filteredIssues,
    groupedIssues,
    fetchIssues,
  };
});
