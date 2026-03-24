import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GitLabMergeRequest, ItemPreference } from '../lib/types';
import { computeMRScore, sortByScore, groupByProject, setPriorityLabels } from '../lib/scoring';
import { api } from '../lib/api';
import { useConfigStore } from './config';

export type MRGroupBy = 'project' | 'priority' | 'none';

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

  /** Merge assigned + followed, deduplicando por project_path + iid */
  const allMRs = computed(() => {
    const seen = new Set<string>();
    const result: GitLabMergeRequest[] = [];
    for (const mr of mergeRequests.value) {
      const key = `${mr.project_path}#${mr.iid}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(mr);
      }
    }
    for (const mr of followedMRs.value) {
      const key = `${mr.project_path}#${mr.iid}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(mr);
      }
    }
    return result;
  });

  const scoredMRs = computed(() => {
    const followedKeys = new Set(followedMRs.value.map(f => `${f.project_path}#${f.iid}`));
    const scored = allMRs.value.map(mr => {
      const pref = preferences.value.get(mr.id);
      const manualPriority = pref?.manual_score ?? mr.manual_priority ?? 0;
      const mrWithPref = { ...mr, manual_priority: manualPriority };
      const isFollowed = followedKeys.has(`${mr.project_path}#${mr.iid}`);
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
      result = result.filter(mr =>
        mr.assignees?.some(a => a.username === currentUsername.value)
      );
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
      const mp = mr.manual_priority ?? 0;
      let key: string;
      if (mp >= 100) key = 'Critica';
      else if (mp >= 75) key = 'Alta';
      else if (mp >= 50) key = 'Media';
      else if (mp > 0) key = 'Baja';
      else key = 'Sin prioridad';
      if (!groups[key]) groups[key] = [];
      groups[key].push(mr);
    }
    const sorted: Record<string, typeof filteredMRs.value> = {};
    for (const label of ['Critica', 'Alta', 'Media', 'Baja', 'Sin prioridad']) {
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
    const updated = new Map(preferences.value);
    updated.set(mrId, { ...existing, ...data } as ItemPreference);
    preferences.value = updated;
  }

  async function followMR(mrId: number, meta?: { source?: string; project_path?: string; iid?: number; title?: string }) {
    await updatePreference(mrId, { followed: true, ...meta });
    await fetchFollowedMRs();
  }

  async function unfollowMR(mrId: number) {
    await updatePreference(mrId, { followed: false });
    await fetchFollowedMRs();
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
