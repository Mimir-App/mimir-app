import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabIssue, ItemPreference } from '../lib/types';
import { computeIssueScore, sortByScore, groupByProject, setPriorityLabels } from '../lib/scoring';
import { api } from '../lib/api';
import { useConfigStore } from './config';

export type IssueGroupBy = 'project' | 'priority' | 'none';

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
  const sourceFilter = ref<'all' | 'gitlab' | 'github'>('all');
  const projectFilter = ref<string[]>([]);

  /** Merge assigned + followed, deduplicando por project_path + iid */
  const allIssues = computed(() => {
    const seen = new Set<string>();
    const result: GitLabIssue[] = [];
    for (const issue of issues.value) {
      const key = `${issue.project_path}#${issue.iid}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(issue);
      }
    }
    for (const issue of followedIssues.value) {
      const key = `${issue.project_path}#${issue.iid}`;
      if (!seen.has(key)) {
        seen.add(key);
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

    // Filtro por fuente
    if (sourceFilter.value !== 'all') {
      result = result.filter(i => (i as any)._source === sourceFilter.value);
    }

    // Filtro por proyecto(s)
    if (projectFilter.value.length > 0) {
      result = result.filter(i => projectFilter.value.includes(i.project_path));
    }

    // Filtro activo (asignadas/seguidas)
    if (activeFilter.value === 'assigned') {
      result = result.filter(i => !i._followed || issues.value.some(a => a.id === i.id));
    } else if (activeFilter.value === 'followed') {
      result = result.filter(i => i._followed);
    }

    // Filtro de texto
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

  /** Proyectos disponibles en las issues cargadas */
  const availableProjects = computed(() => {
    const projects = new Set<string>();
    for (const issue of allIssues.value) {
      if (issue.project_path) projects.add(issue.project_path);
    }
    return Array.from(projects).sort();
  });

  const groupedByProject = computed(() => groupByProject(filteredIssues.value));

  const groupedByPriority = computed(() => {
    const groups: Record<string, (typeof filteredIssues.value)> = {};
    for (const issue of filteredIssues.value) {
      const mp = issue.manual_priority ?? 0;
      let key: string;
      if (mp >= 100) key = 'Critica';
      else if (mp >= 75) key = 'Alta';
      else if (mp >= 50) key = 'Media';
      else if (mp > 0) key = 'Baja';
      else key = 'Sin prioridad';
      if (!groups[key]) groups[key] = [];
      groups[key].push(issue);
    }
    const sorted: Record<string, typeof filteredIssues.value> = {};
    for (const label of ['Critica', 'Alta', 'Media', 'Baja', 'Sin prioridad']) {
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

  async function searchIssues(query: string, source: 'all' | 'gitlab' | 'github' = 'all') {
    if (query.length < 2) { searchResults.value = []; return; }
    searchLoading.value = true;
    try {
      const results: GitLabIssue[] = [];
      if (source !== 'github') results.push(...await api.searchGitlabIssues(query));
      if (source !== 'gitlab') results.push(...await api.searchGithubIssues(query));
      searchResults.value = results;
    } finally {
      searchLoading.value = false;
    }
  }

  async function updatePreference(issueId: number, data: Partial<ItemPreference>) {
    await api.updateItemPreferences('issue', issueId, data);
    const existing = preferences.value.get(issueId) || { item_id: issueId, item_type: 'issue' as const, manual_score: 0, followed: false };
    const updated = new Map(preferences.value);
    updated.set(issueId, { ...existing, ...data } as ItemPreference);
    preferences.value = updated;
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
    sourceFilter,
    projectFilter,
    availableProjects,
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
