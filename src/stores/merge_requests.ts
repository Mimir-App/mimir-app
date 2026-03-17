import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabMergeRequest, ItemPreference } from '../lib/types';
import { computeMRScore, sortByScore, groupByProject, setPriorityLabels } from '../lib/scoring';
import { api } from '../lib/api';
import { useConfigStore } from './config';

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
  const preferences = ref<Map<number, ItemPreference>>(new Map());
  const followedMRs = ref<GitLabMergeRequest[]>([]);
  const searchResults = ref<GitLabMergeRequest[]>([]);
  const searchLoading = ref(false);
  const activeFilter = ref<'all' | 'assigned' | 'reviewer' | 'followed'>('all');
  const currentUsername = ref('');

  /** Merge assigned + followed, deduplicando por id */
  const allMRs = computed(() => {
    const seen = new Set<number>();
    const result: GitLabMergeRequest[] = [];
    for (const mr of mergeRequests.value) {
      if (!seen.has(mr.id)) {
        seen.add(mr.id);
        result.push(mr);
      }
    }
    for (const mr of followedMRs.value) {
      if (!seen.has(mr.id)) {
        seen.add(mr.id);
        result.push(mr);
      }
    }
    return result;
  });

  const scoredMRs = computed(() => {
    const scored = allMRs.value.map(mr => {
      const pref = preferences.value.get(mr.id);
      const manualPriority = pref?.manual_score ?? mr.manual_priority ?? 0;
      const mrWithPref = { ...mr, manual_priority: manualPriority };
      const isFollowed = followedMRs.value.some(f => f.id === mr.id);
      return {
        ...mrWithPref,
        score: computeMRScore(mrWithPref),
        _followed: isFollowed,
      };
    });
    return sortByScore(scored);
  });

  const filteredMRs = computed(() => {
    let result = scoredMRs.value;

    // Aplicar filtro activo
    if (activeFilter.value === 'assigned') {
      result = result.filter(mr => !mr._followed || mergeRequests.value.some(a => a.id === mr.id));
    } else if (activeFilter.value === 'reviewer') {
      result = result.filter(mr => mr.reviewers.some(r => r.username === currentUsername.value));
    } else if (activeFilter.value === 'followed') {
      result = result.filter(mr => mr._followed);
    }

    // Aplicar filtro de texto
    if (filterText.value) {
      const q = filterText.value.toLowerCase();
      result = result.filter(
        mr =>
          mr.title.toLowerCase().includes(q) ||
          mr.project_path.toLowerCase().includes(q) ||
          mr.source_branch.toLowerCase().includes(q) ||
          mr.labels.some(l => l.toLowerCase().includes(q))
      );
    }

    return result;
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

  async function fetchPreferences() {
    const prefs = await api.getItemPreferences('mr');
    preferences.value = new Map(prefs.map(p => [p.item_id, p]));
  }

  async function fetchFollowedMRs() {
    followedMRs.value = await api.getFollowedMergeRequests();
  }

  async function fetchUsername() {
    try {
      const user = await api.getGitlabUser();
      currentUsername.value = user.username;
    } catch {
      // Silenciar error
    }
  }

  async function searchMRs(query: string) {
    if (query.length < 2) { searchResults.value = []; return; }
    searchLoading.value = true;
    try {
      searchResults.value = await api.searchMergeRequests(query);
    } finally {
      searchLoading.value = false;
    }
  }

  async function updatePreference(mrId: number, data: Partial<ItemPreference>) {
    await api.updateItemPreferences('mr', mrId, data);
    const existing = preferences.value.get(mrId) || { item_id: mrId, item_type: 'mr' as const, manual_score: 0, followed: false };
    preferences.value.set(mrId, { ...existing, ...data } as ItemPreference);
  }

  async function followMR(mrId: number) {
    await updatePreference(mrId, { followed: true });
    await fetchFollowedMRs();
  }

  async function unfollowMR(mrId: number) {
    await updatePreference(mrId, { followed: false });
    followedMRs.value = followedMRs.value.filter(mr => mr.id !== mrId);
  }

  async function fetchMergeRequests() {
    loading.value = true;
    error.value = null;
    try {
      // Aplicar priority labels desde config
      const configStore = useConfigStore();
      if (configStore.config.gitlab_priority_labels?.length) {
        setPriorityLabels(configStore.config.gitlab_priority_labels);
      }

      mergeRequests.value = await api.getMergeRequests() as GitLabMergeRequest[];
      await fetchPreferences();
      await fetchFollowedMRs();
      await fetchUsername();
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
    preferences,
    followedMRs,
    searchResults,
    searchLoading,
    activeFilter,
    currentUsername,
    allMRs,
    scoredMRs,
    filteredMRs,
    groupedMRs,
    fetchMergeRequests,
    fetchPreferences,
    fetchFollowedMRs,
    searchMRs,
    updatePreference,
    followMR,
    unfollowMR,
  };
});
