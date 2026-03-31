<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { GitLabIssue, GitLabMergeRequest } from '../lib/types';
import { api } from '../lib/api';
import { useConfigStore } from '../stores/config';
import { useIssuesStore } from '../stores/issues';
import { useMergeRequestsStore } from '../stores/merge_requests';
import ViewToolbar from '../components/shared/ViewToolbar.vue';
import DiscoverTable from '../components/discover/DiscoverTable.vue';
import IssueDetailModal from '../components/issues/IssueDetailModal.vue';
import MRDetailModal from '../components/merge_requests/MRDetailModal.vue';
import ContextMenu from '../components/shared/ContextMenu.vue';
import type { MenuEntry } from '../components/shared/ContextMenu.vue';
import CustomSelect from '../components/shared/CustomSelect.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import EmptyState from '../components/shared/EmptyState.vue';
import { Eye, ExternalLink, XCircle, Star, Link, Hash } from 'lucide-vue-next';

type DiscoverItem = (GitLabIssue | GitLabMergeRequest) & { _type?: string; _source?: string };

const configStore = useConfigStore();
const issuesStore = useIssuesStore();
const mrStore = useMergeRequestsStore();

// Filters
const source = ref<'all' | 'github' | 'gitlab'>('all');
const itemType = ref<'all' | 'issue' | 'mr'>('all');
const repo = ref('');
const query = ref('');
const limit = ref(20);

// Results
const allResults = ref<DiscoverItem[]>([]);
const loading = ref(false);
const searched = ref(false);
const currentPage = ref(1);
const hasMore = ref(false);

const results = computed(() => allResults.value);
const totalCount = computed(() => allResults.value.length);

// Available sources
const hasGitlab = computed(() => Boolean(configStore.config.gitlab_url && configStore.config.gitlab_token_stored));
const hasGithub = computed(() => Boolean(configStore.config.github_token_stored));
const hasBoth = computed(() => hasGitlab.value && hasGithub.value);

// Options para CustomSelect
const sourceOptions = computed(() => [
  { value: 'all' as string | null, label: 'Todas' },
  { value: 'gitlab' as string | null, label: 'GitLab' },
  { value: 'github' as string | null, label: 'GitHub' },
]);

const typeOptions = computed(() => [
  { value: 'all' as string | null, label: 'Todos' },
  { value: 'issue' as string | null, label: 'Issues' },
  { value: 'mr' as string | null, label: 'MRs / PRs' },
]);

const repoOptions = computed(() => [
  { value: '' as string | null, label: 'Todos los repos' },
  ...availableRepos.value.map(r => ({ value: r as string | null, label: r })),
]);

const limitOptions = computed(() => [
  { value: 10 as number | null, label: '10' },
  { value: 20 as number | null, label: '20' },
  { value: 50 as number | null, label: '50' },
  { value: 100 as number | null, label: '100' },
]);

// Auto-set source
if (!hasGitlab.value && hasGithub.value) source.value = 'github';
if (hasGitlab.value && !hasGithub.value) source.value = 'gitlab';

// Available repos
const availableRepos = computed(() => {
  const repos = new Set<string>();
  for (const i of issuesStore.allIssues) { if (i.project_path) repos.add(i.project_path); }
  for (const m of mrStore.mergeRequests ?? []) { if (m.project_path) repos.add(m.project_path); }
  return Array.from(repos).sort();
});

// Counter text
const counterText = computed(() => {
  if (!searched.value) return '';
  if (totalCount.value === 0) return 'Sin resultados';
  return `Mostrando ${Math.min(limit.value, totalCount.value)} de ${totalCount.value} resultados`;
});

// Search
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function triggerSearch() {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (query.value.length < 2) {
    allResults.value = [];
    searched.value = false;
    return;
  }
  debounceTimer = setTimeout(() => executeSearch(), 300);
}

async function executeSearch(page: number = 1) {
  loading.value = true;
  searched.value = true;
  try {
    const q = repo.value ? `repo:${repo.value} ${query.value}` : query.value;
    const promises: Promise<DiscoverItem[]>[] = [];

    const searchGitlab = source.value !== 'github' && hasGitlab.value;
    const searchGithub = source.value !== 'gitlab' && hasGithub.value;

    if (itemType.value !== 'mr') {
      if (searchGitlab) promises.push(api.searchGitlabIssues(q, page) as Promise<DiscoverItem[]>);
      if (searchGithub) promises.push(api.searchGithubIssues(q, page) as Promise<DiscoverItem[]>);
    }
    if (itemType.value !== 'issue') {
      if (searchGitlab) promises.push(api.searchMergeRequests(q, page) as Promise<DiscoverItem[]>);
      if (searchGithub) promises.push(api.searchGithubPullRequests(q, page) as Promise<DiscoverItem[]>);
    }

    const arrays = await Promise.all(promises);
    const combined = arrays.flat();
    combined.sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''));

    if (page === 1) {
      allResults.value = combined;
    } else {
      // Acumular resultados evitando duplicados
      const existingIds = new Set(allResults.value.map(r => `${r.project_path}#${r.iid}`));
      const newItems = combined.filter(r => !existingIds.has(`${r.project_path}#${r.iid}`));
      allResults.value = [...allResults.value, ...newItems];
    }
    currentPage.value = page;
    hasMore.value = combined.length >= 20;
  } catch {
    if (page === 1) allResults.value = [];
  } finally {
    loading.value = false;
  }
}

watch(query, triggerSearch);
watch([source, itemType, repo], () => { if (query.value.length >= 2) { currentPage.value = 1; executeSearch(); } });

async function showMore() {
  await executeSearch(currentPage.value + 1);
}

async function refresh() {
  if (query.value.length >= 2) await executeSearch();
}

// Followed keys (project_path#iid)
const localFollowedKeys = ref(new Set<string>());

const followedKeys = computed(() => {
  const keys = new Set(localFollowedKeys.value);
  for (const i of issuesStore.followedIssues) keys.add(`${i.project_path}#${i.iid}`);
  if (mrStore.followedMRs) {
    for (const m of mrStore.followedMRs) keys.add(`${m.project_path}#${m.iid}`);
  }
  return keys;
});

// Init followed data from stores
issuesStore.fetchFollowedIssues();
mrStore.fetchFollowedMRs();

// Track item types and keys for unfollow
const itemTypeMap = new Map<number, string>();
const itemKeyMap = new Map<number, string>();

async function followItem(item: DiscoverItem) {
  const type = item._type === 'merge_request' ? 'mr' : 'issue';
  await api.updateItemPreferences(type, item.id, {
    followed: true,
    source: item._source,
    project_path: item.project_path,
    iid: item.iid,
    title: item.title,
  });
  const key = `${item.project_path}#${item.iid}`;
  localFollowedKeys.value = new Set([...localFollowedKeys.value, key]);
  itemTypeMap.set(item.id, type);
  itemKeyMap.set(item.id, key);
  if (type === 'issue') issuesStore.fetchFollowedIssues();
  else mrStore.fetchFollowedMRs();
}

async function unfollowItem(itemId: number) {
  const type = itemTypeMap.get(itemId) || 'issue';
  await api.updateItemPreferences(type, itemId, { followed: false });
  const key = itemKeyMap.get(itemId);
  if (key) {
    const updated = new Set(localFollowedKeys.value);
    updated.delete(key);
    localFollowedKeys.value = updated;
  }
  if (type === 'issue') issuesStore.fetchFollowedIssues();
  else mrStore.fetchFollowedMRs();
}

// Detail modal
const selectedItem = ref<DiscoverItem | null>(null);
const showIssueDetail = ref(false);
const showMRDetail = ref(false);

function openDetail(item: DiscoverItem) {
  selectedItem.value = item;
  if (item._type === 'merge_request') {
    showMRDetail.value = true;
  } else {
    showIssueDetail.value = true;
  }
}

// Context menu
const ctxVisible = ref(false);
const ctxX = ref(0);
const ctxY = ref(0);
const ctxItems = ref<MenuEntry[]>([]);

function onContextMenu(item: DiscoverItem, e: MouseEvent) {
  const isFollowed = followedKeys.value.has(`${item.project_path}#${item.iid}`);
  const isGithub = item._source === 'github';

  async function openUrl(url: string) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('plugin:opener|open_url', { url });
    } catch {
      window.open(url, '_blank');
    }
  }

  ctxItems.value = [
    { label: 'Ver detalle', icon: Eye, action: () => openDetail(item) },
    { label: `Ir a ${isGithub ? 'GitHub' : 'GitLab'}`, icon: ExternalLink, action: () => openUrl(item.web_url) },
    { separator: true },
    isFollowed
      ? { label: 'Dejar de seguir', icon: XCircle, action: () => unfollowItem(item.id), danger: true }
      : { label: 'Seguir', icon: Star, action: () => followItem(item) },
    { separator: true },
    { label: 'Copiar enlace', icon: Link, action: () => navigator.clipboard.writeText(item.web_url) },
    { label: 'Copiar referencia', icon: Hash, action: () => navigator.clipboard.writeText(`${item.project_path}#${item.iid}`) },
  ];
  ctxX.value = e.clientX;
  ctxY.value = e.clientY;
  ctxVisible.value = true;
}
</script>

<template>
  <div class="discover-view">
    <!-- Toolbar with search filters -->
    <ViewToolbar
      :showFilter="false"
      :showCollapse="false"
      :refreshing="loading"
      @refresh="refresh"
    >
      <!-- Filter selects inside toolbar -->
      <div class="discover-filters">
        <CustomSelect
          v-if="hasBoth"
          :modelValue="source"
          @update:modelValue="(v: string | number | null) => source = (v as 'all' | 'github' | 'gitlab')"
          :options="sourceOptions"
          class="filter-custom-select"
        />

        <CustomSelect
          :modelValue="itemType"
          @update:modelValue="(v: string | number | null) => itemType = (v as 'all' | 'issue' | 'mr')"
          :options="typeOptions"
          class="filter-custom-select"
        />

        <CustomSelect
          :modelValue="repo"
          @update:modelValue="(v: string | number | null) => repo = (v as string) ?? ''"
          :options="repoOptions"
          :searchable="availableRepos.length > 5"
          class="filter-custom-select filter-repo"
        />

        <input
          v-model="query"
          type="text"
          class="discover-search"
          placeholder="Buscar..."
          aria-label="Buscar issues y merge requests"
        />

        <CustomSelect
          :modelValue="limit"
          @update:modelValue="(v: string | number | null) => limit = Number(v) || 20"
          :options="limitOptions"
          class="filter-custom-select filter-limit"
        />
      </div>
    </ViewToolbar>

    <!-- Counter -->
    <div v-if="counterText" class="results-counter">{{ counterText }}</div>

    <!-- Results -->
    <LoadingState v-if="loading && allResults.length === 0" text="Buscando..." />

    <DiscoverTable
      v-else-if="results.length > 0"
      :items="results"
      :followed-keys="followedKeys"
      @select="openDetail"
      @follow="(id) => { const item = allResults.find(r => r.id === id); if (item) followItem(item); }"
      @unfollow="unfollowItem"
      @contextmenu="onContextMenu"
    />

    <EmptyState
      v-else-if="searched && !loading"
      text="No se encontraron resultados"
    />

    <EmptyState
      v-else-if="!searched"
      text="Escribe al menos 2 caracteres para buscar"
    />

    <!-- Show more -->
    <div v-if="hasMore && allResults.length > 0" class="show-more">
      <button class="btn-show-more" @click="showMore" :disabled="loading">
        {{ loading ? 'Cargando...' : 'Mostrar más' }}
      </button>
    </div>

    <!-- Detail modals -->
    <IssueDetailModal
      :issue="selectedItem as GitLabIssue | null"
      :open="showIssueDetail"
      @close="showIssueDetail = false"
    />
    <MRDetailModal
      :mr="selectedItem as GitLabMergeRequest | null"
      :open="showMRDetail"
      @close="showMRDetail = false"
    />

    <!-- Context menu -->
    <ContextMenu
      v-if="ctxVisible"
      :items="ctxItems"
      :x="ctxX"
      :y="ctxY"
      @close="ctxVisible = false"
    />
  </div>
</template>

<style scoped>
.discover-view {
  width: 100%;
}

.discover-filters {
  display: flex;
  gap: 6px;
  flex: 1;
  align-items: center;
}

.filter-custom-select {
  min-width: 100px;
  font-size: 12px;
}

.filter-custom-select.filter-repo {
  min-width: 140px;
}

.filter-custom-select.filter-limit {
  min-width: 60px;
  max-width: 70px;
}

.discover-search {
  flex: 1;
  min-width: 120px;
  padding: 6px 10px;
  font-size: 13px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-right: none;
  outline: none;
}

.discover-search:focus {
  border-color: var(--accent);
}

.discover-search::placeholder {
  color: var(--text-secondary);
}

/* Counter */
.results-counter {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding-left: 2px;
}

/* Show more */
.show-more {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.btn-show-more {
  padding: 8px 24px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-show-more:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
}
</style>
