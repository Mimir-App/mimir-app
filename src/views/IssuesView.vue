<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import type { GitLabIssue } from '../lib/types';
import { useIssuesStore } from '../stores/issues';
import { usePolling } from '../composables/usePolling';
import { provideCollapseAll } from '../composables/useCollapseAll';
import ViewToolbar from '../components/shared/ViewToolbar.vue';
import CustomSelect from '../components/shared/CustomSelect.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import StatusBanner from '../components/shared/StatusBanner.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import EmptyState from '../components/shared/EmptyState.vue';
import IssueTable from '../components/issues/IssueTable.vue';
import IssueDetailModal from '../components/issues/IssueDetailModal.vue';

const issuesStore = useIssuesStore();
const refreshing = ref(false);
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
usePolling(() => issuesStore.fetchIssues());

// Search state
const searchQuery = ref('');
const showSearchDropdown = ref(false);
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
const searchContainer = ref<HTMLElement | null>(null);

// Detail modal state
const selectedIssue = ref<GitLabIssue | null>(null);
const showDetail = ref(false);

// Set of followed issue IDs for the dot indicator
const followedIds = computed(() => {
  return new Set(issuesStore.followedIssues.map(i => i.id));
});

// Filter tabs
const filterTabs: { value: 'all' | 'assigned' | 'followed'; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'assigned', label: 'Asignadas' },
  { value: 'followed', label: 'Seguidas' },
];

async function refresh() {
  refreshing.value = true;
  try { await issuesStore.fetchIssues(); } finally { refreshing.value = false; }
}

function openIssueDetail(issue: GitLabIssue) {
  selectedIssue.value = issue;
  showDetail.value = true;
}

// Debounced search
watch(searchQuery, (q) => {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (q.length < 2) {
    issuesStore.searchResults = [];
    showSearchDropdown.value = false;
    return;
  }
  debounceTimer = setTimeout(async () => {
    await issuesStore.searchIssues(q);
    showSearchDropdown.value = issuesStore.searchResults.length > 0;
  }, 300);
});

async function handleFollow(issue: GitLabIssue) {
  await issuesStore.followIssue(issue.id);
  // Remove from search results after following
  issuesStore.searchResults = issuesStore.searchResults.filter(r => r.id !== issue.id);
  if (issuesStore.searchResults.length === 0) {
    showSearchDropdown.value = false;
  }
}

function closeSearchDropdown() {
  showSearchDropdown.value = false;
}

// Close dropdown on outside click
function handleClickOutside(e: MouseEvent) {
  if (searchContainer.value && !searchContainer.value.contains(e.target as Node)) {
    closeSearchDropdown();
  }
}

function handleSearchKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closeSearchDropdown();
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
  if (debounceTimer) clearTimeout(debounceTimer);
});
</script>

<template>
  <div class="issues-view">
    <!-- Search bar -->
    <div ref="searchContainer" class="search-section">
      <div class="search-input-wrap">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="Buscar issues en GitLab..."
          @keydown="handleSearchKeydown"
        />
        <span v-if="issuesStore.searchLoading" class="search-spinner"></span>
      </div>
      <div v-if="showSearchDropdown" class="search-dropdown">
        <div
          v-for="result in issuesStore.searchResults"
          :key="result.id"
          class="search-result"
        >
          <div class="search-result-info">
            <span class="search-result-title">{{ result.title }}</span>
            <span class="search-result-meta">
              {{ result.project_path }}
              <span v-for="label in result.labels.slice(0, 3)" :key="label" class="search-label-tag">{{ label }}</span>
            </span>
          </div>
          <button class="follow-btn" @click.stop="handleFollow(result)">Seguir</button>
        </div>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        class="filter-tab"
        :class="{ active: issuesStore.activeFilter === tab.value }"
        @click="issuesStore.activeFilter = tab.value"
      >{{ tab.label }}</button>
    </div>

    <ViewToolbar
      v-model:filter="issuesStore.filterText"
      filterPlaceholder="Filtrar issues por titulo, proyecto o label..."
      showCollapse
      :allExpanded="allExpanded"
      :refreshing="refreshing"
      :loading="issuesStore.loading"
      @refresh="refresh"
      @toggleCollapse="toggleCollapseAll"
    >
      <CustomSelect v-model="issuesStore.groupBy" :options="[
        { value: 'project', label: 'Por proyecto' },
        { value: 'priority', label: 'Por prioridad' },
        { value: 'none', label: 'Sin agrupar' },
      ]" />
    </ViewToolbar>

    <StatusBanner v-if="issuesStore.error" type="error">{{ issuesStore.error }}</StatusBanner>
    <LoadingState v-if="issuesStore.loading && issuesStore.issues.length === 0" text="Cargando issues..." />

    <template v-else>
      <CollapsibleGroup
        v-for="(issues, project) in issuesStore.groupedIssues"
        :key="project"
        :label="String(project)"
        :count="issues.length"
      >
        <IssueTable :issues="issues" :followedIds="followedIds" @select="openIssueDetail" />
      </CollapsibleGroup>

      <EmptyState v-if="issuesStore.filteredIssues.length === 0 && !issuesStore.loading" text="Sin issues que mostrar" />
    </template>

    <IssueDetailModal :issue="selectedIssue" :open="showDetail" @close="showDetail = false" />
  </div>
</template>

<style scoped>
/* Search section */
.search-section {
  position: relative;
  margin-bottom: 12px;
}

.search-input-wrap {
  position: relative;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: var(--accent);
}

.search-input::placeholder {
  color: var(--text-secondary);
}

.search-spinner {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: translateY(-50%) rotate(360deg); }
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 6px 6px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.search-result {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  gap: 8px;
}

.search-result:last-child {
  border-bottom: none;
}

.search-result:hover {
  background: var(--bg-hover);
}

.search-result-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.search-result-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-result-meta {
  font-size: 11px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.search-label-tag {
  display: inline-block;
  padding: 0 4px;
  background: var(--bg-card);
  border-radius: 3px;
  font-size: 10px;
  color: var(--text-secondary);
}

.follow-btn {
  flex-shrink: 0;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.follow-btn:hover {
  background: var(--accent-hover);
}

/* Filter tabs */
.filter-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}

.filter-tab {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.filter-tab.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
</style>
