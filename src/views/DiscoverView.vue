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
import LoadingState from '../components/shared/LoadingState.vue';
import EmptyState from '../components/shared/EmptyState.vue';

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

const results = computed(() => allResults.value.slice(0, limit.value));
const totalCount = computed(() => allResults.value.length);

// Available sources
const hasGitlab = computed(() => Boolean(configStore.config.gitlab_url && configStore.config.gitlab_token_stored));
const hasGithub = computed(() => Boolean(configStore.config.github_token_stored));
const hasBoth = computed(() => hasGitlab.value && hasGithub.value);

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

async function executeSearch() {
  loading.value = true;
  searched.value = true;
  try {
    const q = repo.value ? `repo:${repo.value} ${query.value}` : query.value;
    const promises: Promise<DiscoverItem[]>[] = [];

    const searchGitlab = source.value !== 'github' && hasGitlab.value;
    const searchGithub = source.value !== 'gitlab' && hasGithub.value;

    if (itemType.value !== 'mr') {
      if (searchGitlab) promises.push(api.searchGitlabIssues(q) as Promise<DiscoverItem[]>);
      if (searchGithub) promises.push(api.searchGithubIssues(q) as Promise<DiscoverItem[]>);
    }
    if (itemType.value !== 'issue') {
      if (searchGitlab) promises.push(api.searchMergeRequests(q) as Promise<DiscoverItem[]>);
      if (searchGithub) promises.push(api.searchGithubPullRequests(q) as Promise<DiscoverItem[]>);
    }

    const arrays = await Promise.all(promises);
    const combined = arrays.flat();
    combined.sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''));
    allResults.value = combined;
  } catch {
    allResults.value = [];
  } finally {
    loading.value = false;
  }
}

watch(query, triggerSearch);
watch([source, itemType, repo], () => { if (query.value.length >= 2) executeSearch(); });

function showMore() { limit.value += 20; }

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
    { label: 'Ver detalle', icon: '\u25B6', action: () => openDetail(item) },
    { label: `Ir a ${isGithub ? 'GitHub' : 'GitLab'}`, icon: '\u2197', action: () => openUrl(item.web_url) },
    { separator: true },
    isFollowed
      ? { label: 'Dejar de seguir', icon: '\u2716', action: () => unfollowItem(item.id), danger: true }
      : { label: 'Seguir', icon: '\u2605', action: () => followItem(item) },
    { separator: true },
    { label: 'Copiar enlace', icon: '\u{1F517}', action: () => navigator.clipboard.writeText(item.web_url) },
    { label: 'Copiar referencia', icon: '#', action: () => navigator.clipboard.writeText(`${item.project_path}#${item.iid}`) },
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
        <select v-if="hasBoth" v-model="source" class="filter-select">
          <option value="all">Todas</option>
          <option value="gitlab">GitLab</option>
          <option value="github">GitHub</option>
        </select>

        <select v-model="itemType" class="filter-select">
          <option value="all">Todos</option>
          <option value="issue">Issues</option>
          <option value="mr">MRs / PRs</option>
        </select>

        <select v-model="repo" class="filter-select">
          <option value="">Todos los repos</option>
          <option v-for="r in availableRepos" :key="r" :value="r">{{ r }}</option>
        </select>

        <input
          v-model="query"
          type="text"
          class="discover-search"
          placeholder="Buscar..."
        />

        <select v-model.number="limit" class="filter-select limit-select">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
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
    <div v-if="results.length < totalCount && results.length > 0" class="show-more">
      <button class="btn-show-more" @click="showMore">
        Mostrar mas ({{ totalCount - results.length }} restantes)
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
  gap: 0;
  flex: 1;
}

.filter-select {
  padding: 6px 10px;
  font-size: 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-right: none;
  outline: none;
  cursor: pointer;
}

.filter-select:first-child {
  border-radius: 4px 0 0 4px;
}

.filter-select:focus {
  border-color: var(--accent);
  z-index: 1;
  position: relative;
}

.limit-select {
  width: 55px;
  border-right: 1px solid var(--border);
  border-radius: 0 4px 4px 0;
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
