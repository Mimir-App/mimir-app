<script setup lang="ts">
import { ref, computed } from 'vue';
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
import ContextMenu from '../components/shared/ContextMenu.vue';
import type { MenuEntry } from '../components/shared/ContextMenu.vue';
import { X } from 'lucide-vue-next';

const issuesStore = useIssuesStore();
const refreshing = ref(false);
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
usePolling(() => issuesStore.fetchIssues());

// Detail modal state
const selectedIssue = ref<GitLabIssue | null>(null);
const showDetail = ref(false);

// Set of followed issue keys for the dot indicator
const followedKeys = computed(() => {
  return new Set(issuesStore.followedIssues.map(i => `${i.project_path}#${i.iid}`));
});

// Filter tabs
const filterTabs: { value: 'all' | 'assigned' | 'followed'; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'assigned', label: 'Asignadas' },
  { value: 'followed', label: 'Seguidas' },
];

const activeSources = computed(() => {
  const sources = new Set<string>();
  for (const issue of issuesStore.allIssues) {
    if ((issue as any)._source) sources.add((issue as any)._source);
  }
  return sources;
});

const sourceTabs = computed(() => {
  const tabs: { value: 'all' | 'gitlab' | 'github'; label: string }[] = [];
  const hasGitlab = activeSources.value.has('gitlab');
  const hasGithub = activeSources.value.has('github');
  if (hasGitlab && hasGithub) {
    tabs.push({ value: 'all', label: 'Todas' });
  }
  if (hasGitlab) tabs.push({ value: 'gitlab', label: 'GitLab' });
  if (hasGithub) tabs.push({ value: 'github', label: 'GitHub' });
  return tabs;
});

// Project filter
const projectQuery = ref('');
const showProjectDropdown = ref(false);
const projectSuggestions = computed(() => {
  if (!projectQuery.value) return issuesStore.availableProjects;
  const q = projectQuery.value.toLowerCase();
  return issuesStore.availableProjects.filter(p => p.toLowerCase().includes(q));
});

function selectProject(project: string) {
  if (!issuesStore.projectFilter.includes(project)) {
    issuesStore.projectFilter.push(project);
  }
  projectQuery.value = '';
  showProjectDropdown.value = false;
}

function removeProject(project: string) {
  issuesStore.projectFilter = issuesStore.projectFilter.filter(p => p !== project);
}

function clearProjectFilter() {
  issuesStore.projectFilter = [];
  projectQuery.value = '';
}

function hideProjectDropdown() {
  window.setTimeout(() => { showProjectDropdown.value = false; }, 150);
}

async function onUpdateScore(issueId: number, value: number) {
  await issuesStore.updatePreference(issueId, { manual_score: value });
}

async function onUnfollow(issueId: number) {
  await issuesStore.unfollowIssue(issueId);
}

// --- Context menu ---
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuItems = ref<MenuEntry[]>([]);

function onContextMenu(issue: GitLabIssue, e: MouseEvent) {
  e.preventDefault();
  const isFollowed = followedKeys.value.has(`${issue.project_path}#${issue.iid}`);
  const isGithub = issue._source === 'github';
  const currentManual = issue.manual_priority ?? 0;

  async function addScore(delta: number) {
    await issuesStore.updatePreference(issue.id, { manual_score: currentManual + delta });
  }

  async function openUrl(url: string) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('plugin:opener|open_url', { url });
    } catch {
      window.open(url, '_blank');
    }
  }

  const items: MenuEntry[] = [
    { label: 'Ver detalle', icon: '\u25B6', action: () => openIssueDetail(issue) },
    { label: `Ir a ${isGithub ? 'GitHub' : 'GitLab'}`, icon: '\u2197', action: () => openUrl(issue.web_url) },
    { separator: true },
    isFollowed
      ? { label: 'Dejar de seguir', icon: '\u2716', action: () => issuesStore.unfollowIssue(issue.id), danger: true }
      : { label: 'Seguir', icon: '\u2605', action: () => issuesStore.followIssue(issue.id, {
            source: issue._source,
            project_path: issue.project_path,
            iid: issue.iid,
            title: issue.title,
          })},
    { separator: true },
    { label: `Score (${currentManual})`, icon: '#', action: () => {}, disabled: true },
    {
      label: 'Modificar score',
      icon: '\u25B2\u25BC',
      action: () => {},
      select: {
        options: [
          { label: '+100', value: 100 },
          { label: '+50', value: 50 },
          { label: '+10', value: 10 },
          { label: '+5', value: 5 },
          { label: '+1', value: 1 },
          { label: '-1', value: -1 },
          { label: '-5', value: -5 },
          { label: '-10', value: -10 },
          { label: '-50', value: -50 },
          { label: '-100', value: -100 },
        ],
        onSelect: (val: number) => addScore(val),
      },
    },
    { separator: true },
    { label: 'Copiar enlace', icon: '\u{1F517}', action: () => navigator.clipboard.writeText(issue.web_url) },
    { label: 'Copiar referencia', icon: '#', action: () => navigator.clipboard.writeText(`${issue.project_path}#${issue.iid}`) },
    { separator: true },
    { label: 'Ocultar', icon: '\u{1F6AB}', action: () => issuesStore.hideIssue(issue.project_path, issue.iid) },
    { separator: true },
    { label: 'Recargar issues', icon: '\u21BB', action: () => refresh() },
  ];

  contextMenuItems.value = items;
  contextMenuX.value = e.clientX;
  contextMenuY.value = e.clientY;
  contextMenuVisible.value = true;
}

async function refresh() {
  refreshing.value = true;
  try { await issuesStore.fetchIssues(); } finally { refreshing.value = false; }
}

function openIssueDetail(issue: GitLabIssue) {
  selectedIssue.value = issue;
  showDetail.value = true;
}

</script>

<template>
  <div class="issues-view">
    <!-- Filter tabs -->
    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          class="filter-tab"
          :class="{ active: issuesStore.activeFilter === tab.value }"
          @click="issuesStore.activeFilter = tab.value"
        >{{ tab.label }}</button>
      </div>

      <div class="filter-right">
        <!-- Project filter -->
        <div class="project-filter-group">
          <div v-for="p in issuesStore.projectFilter" :key="p" class="project-chip">
            <span>{{ p.split('/').pop() }}</span>
            <button class="chip-clear" @click="removeProject(p)" :title="p" aria-label="Quitar filtro"><X :size="12" :stroke-width="2" /></button>
          </div>
          <div class="project-filter">
            <input
              v-model="projectQuery"
              type="text"
              class="project-input"
              placeholder="Proyecto..."
              @focus="showProjectDropdown = true"
              @blur="hideProjectDropdown"
            />
            <div v-if="showProjectDropdown && projectSuggestions.length" class="project-dropdown">
              <div
                v-for="project in projectSuggestions"
                :key="project"
                class="project-option"
                :class="{ selected: issuesStore.projectFilter.includes(project) }"
                @mousedown.prevent="selectProject(project)"
              >{{ project }}</div>
            </div>
          </div>
          <button v-if="issuesStore.projectFilter.length" class="chip-clear-all" @click="clearProjectFilter" title="Limpiar filtros" aria-label="Limpiar todos los filtros"><X :size="12" :stroke-width="2" /></button>
        </div>

        <!-- Source tabs -->
        <div v-if="sourceTabs.length > 1" class="filter-tabs source-tabs">
          <button
            v-for="tab in sourceTabs"
            :key="tab.value"
            class="filter-tab source-tab"
            :class="{ active: issuesStore.sourceFilter === tab.value }"
            @click="issuesStore.sourceFilter = tab.value"
          >{{ tab.label }}</button>
        </div>
      </div>
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
      <button
        v-if="issuesStore.hiddenCount > 0"
        class="btn-hidden-toggle"
        :class="{ active: issuesStore.showHidden }"
        @click="issuesStore.showHidden = !issuesStore.showHidden"
        :title="issuesStore.showHidden ? 'Ocultar las tareas ocultas' : `Mostrar ${issuesStore.hiddenCount} tarea(s) oculta(s)`"
      >
        {{ issuesStore.showHidden ? 'Ocultar' : `${issuesStore.hiddenCount} oculta(s)` }}
      </button>
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
        <IssueTable :issues="issues" :followedKeys="followedKeys" @select="openIssueDetail" @update-score="onUpdateScore" @unfollow="onUnfollow" @contextmenu="onContextMenu" />
      </CollapsibleGroup>

      <EmptyState v-if="issuesStore.filteredIssues.length === 0 && !issuesStore.loading" text="Sin issues que mostrar" />
    </template>

    <IssueDetailModal :issue="selectedIssue" :open="showDetail" @close="showDetail = false" />

    <ContextMenu
      v-if="contextMenuVisible"
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      @close="contextMenuVisible = false"
    />
  </div>
</template>

<style scoped>
/* Filter bar */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-tab {
  font-size: 11px;
  padding: 4px 10px;
}

/* Project filter */
.project-filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.project-filter {
  position: relative;
}

.project-input {
  width: 130px;
  padding: 4px 10px;
  font-size: 12px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  outline: none;
}

.project-input:focus {
  border-color: var(--accent);
}

.project-input::placeholder {
  color: var(--text-secondary);
}

.project-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: var(--z-dropdown);
  background: var(--bg-secondary, #2d2d33);
  border: 1px solid var(--accent);
  border-top: none;
  border-radius: 0 0 6px 6px;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.project-option {
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-primary);
}

.project-option:hover {
  background: var(--bg-hover);
}

.project-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  background: var(--accent);
  color: #fff;
  border-radius: 12px;
  white-space: nowrap;
}

.chip-clear {
  background: none;
  border: none;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0.8;
}

.chip-clear:hover {
  opacity: 1;
}

.chip-clear-all {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
}

.chip-clear-all:hover {
  color: var(--error);
}

.project-option.selected {
  opacity: 0.5;
  pointer-events: none;
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

.btn-hidden-toggle {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-hidden-toggle:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}

.btn-hidden-toggle.active {
  background: var(--warning);
  color: #1a1d26;
  border-color: var(--warning);
}
</style>
