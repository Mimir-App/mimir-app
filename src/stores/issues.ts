import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabIssue, ItemPreference } from '../lib/types';
import { computeIssueScore, sortByScore, groupByProject, setPriorityLabels } from '../lib/scoring';
import { api } from '../lib/api';
import { useConfigStore } from './config';

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
  const preferences = ref<Map<number, ItemPreference>>(new Map());
  const followedIssues = ref<GitLabIssue[]>([]);
  const searchResults = ref<GitLabIssue[]>([]);
  const searchLoading = ref(false);
  const activeFilter = ref<'all' | 'assigned' | 'followed'>('all');

  /** Merge assigned + followed, deduplicando por id */
  const allIssues = computed(() => {
    const seen = new Set<number>();
    const result: GitLabIssue[] = [];
    for (const issue of issues.value) {
      if (!seen.has(issue.id)) {
        seen.add(issue.id);
        result.push(issue);
      }
    }
    for (const issue of followedIssues.value) {
      if (!seen.has(issue.id)) {
        seen.add(issue.id);
        result.push(issue);
      }
    }
    return result;
  });

  const scoredIssues = computed(() => {
    const scored = allIssues.value.map(issue => {
      const pref = preferences.value.get(issue.id);
      const manualPriority = pref?.manual_score ?? issue.manual_priority ?? 0;
      const issueWithPref = { ...issue, manual_priority: manualPriority };
      const isFollowed = followedIssues.value.some(f => f.id === issue.id);
      return {
        ...issueWithPref,
        score: computeIssueScore(issueWithPref),
        _followed: isFollowed,
      };
    });
    return sortByScore(scored);
  });

  const filteredIssues = computed(() => {
    let result = scoredIssues.value;

    // Aplicar filtro activo
    if (activeFilter.value === 'assigned') {
      result = result.filter(i => !i._followed || issues.value.some(a => a.id === i.id));
    } else if (activeFilter.value === 'followed') {
      result = result.filter(i => i._followed);
    }

    // Aplicar filtro de texto
    if (filterText.value) {
      const q = filterText.value.toLowerCase();
      result = result.filter(
        i =>
          i.title.toLowerCase().includes(q) ||
          i.project_path.toLowerCase().includes(q) ||
          i.labels.some(l => l.toLowerCase().includes(q))
      );
    }

    return result;
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

  async function fetchPreferences() {
    const prefs = await api.getItemPreferences('issue');
    preferences.value = new Map(prefs.map(p => [p.item_id, p]));
  }

  async function fetchFollowedIssues() {
    followedIssues.value = await api.getFollowedIssues();
  }

  async function searchIssues(query: string) {
    if (query.length < 2) { searchResults.value = []; return; }
    searchLoading.value = true;
    try {
      searchResults.value = await api.searchGitlabIssues(query);
    } finally {
      searchLoading.value = false;
    }
  }

  async function updatePreference(issueId: number, data: Partial<ItemPreference>) {
    await api.updateItemPreferences('issue', issueId, data);
    const existing = preferences.value.get(issueId) || { item_id: issueId, item_type: 'issue' as const, manual_score: 0, followed: false };
    preferences.value.set(issueId, { ...existing, ...data } as ItemPreference);
  }

  async function followIssue(issueId: number) {
    await updatePreference(issueId, { followed: true });
    await fetchFollowedIssues();
  }

  async function unfollowIssue(issueId: number) {
    await updatePreference(issueId, { followed: false });
    followedIssues.value = followedIssues.value.filter(i => i.id !== issueId);
  }

  async function fetchIssues() {
    loading.value = true;
    error.value = null;
    try {
      // Aplicar priority labels desde config
      const configStore = useConfigStore();
      if (configStore.config.gitlab_priority_labels?.length) {
        setPriorityLabels(configStore.config.gitlab_priority_labels);
      }

      issues.value = await api.getIssues() as GitLabIssue[];
      await fetchPreferences();
      await fetchFollowedIssues();
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
    preferences,
    followedIssues,
    searchResults,
    searchLoading,
    activeFilter,
    allIssues,
    scoredIssues,
    filteredIssues,
    groupedIssues,
    fetchIssues,
    fetchPreferences,
    fetchFollowedIssues,
    searchIssues,
    updatePreference,
    followIssue,
    unfollowIssue,
  };
});
