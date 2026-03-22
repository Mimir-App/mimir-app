<script setup lang="ts">
import { ref, computed } from 'vue';
import type { GitLabMergeRequest } from '../lib/types';
import { useMergeRequestsStore } from '../stores/merge_requests';
import { usePolling } from '../composables/usePolling';
import { provideCollapseAll } from '../composables/useCollapseAll';
import ViewToolbar from '../components/shared/ViewToolbar.vue';
import CustomSelect from '../components/shared/CustomSelect.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import StatusBanner from '../components/shared/StatusBanner.vue';
import LoadingState from '../components/shared/LoadingState.vue';
import EmptyState from '../components/shared/EmptyState.vue';
import MRTable from '../components/merge_requests/MRTable.vue';
import MRDetailModal from '../components/merge_requests/MRDetailModal.vue';
import ContextMenu from '../components/shared/ContextMenu.vue';
import type { MenuEntry } from '../components/shared/ContextMenu.vue';

const mrStore = useMergeRequestsStore();
const refreshing = ref(false);
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
usePolling(() => mrStore.fetchMergeRequests());

const selectedMR = ref<GitLabMergeRequest | null>(null);
const showDetail = ref(false);

const followedKeys = computed(() => new Set(mrStore.followedMRs.map(mr => `${mr.project_path}#${mr.iid}`)));

const filterTabs: { value: 'all' | 'assigned' | 'reviewer' | 'followed'; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'assigned', label: 'Asignados' },
  { value: 'reviewer', label: 'Revisor' },
  { value: 'followed', label: 'Seguidos' },
];

async function refresh() {
  refreshing.value = true;
  try { await mrStore.fetchMergeRequests(); } finally { refreshing.value = false; }
}

function openMRDetail(mr: GitLabMergeRequest) {
  selectedMR.value = mr;
  showDetail.value = true;
}

async function onUpdateScore(mrId: number, value: number) {
  await mrStore.updatePreference(mrId, { manual_score: value });
}

async function onUnfollow(mrId: number) {
  await mrStore.unfollowMR(mrId);
}

// --- Context menu ---
const ctxVisible = ref(false);
const ctxX = ref(0);
const ctxY = ref(0);
const ctxItems = ref<MenuEntry[]>([]);

function onContextMenu(mr: GitLabMergeRequest, e: MouseEvent) {
  e.preventDefault();
  const isFollowed = followedKeys.value.has(`${mr.project_path}#${mr.iid}`);
  const isGithub = mr._source === 'github';
  const currentManual = mr.manual_priority ?? 0;

  async function addScore(delta: number) {
    await mrStore.updatePreference(mr.id, { manual_score: currentManual + delta });
  }

  async function openUrl(url: string) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('plugin:opener|open_url', { url });
    } catch {
      window.open(url, '_blank');
    }
  }

  ctxItems.value = [
    { label: 'Ver detalle', icon: '\u25B6', action: () => openMRDetail(mr) },
    { label: `Ir a ${isGithub ? 'GitHub' : 'GitLab'}`, icon: '\u2197', action: () => openUrl(mr.web_url) },
    { separator: true },
    isFollowed
      ? { label: 'Dejar de seguir', icon: '\u2716', action: () => mrStore.unfollowMR(mr.id), danger: true }
      : { label: 'Seguir', icon: '\u2605', action: () => mrStore.followMR(mr.id, {
            source: mr._source,
            project_path: mr.project_path,
            iid: mr.iid,
            title: mr.title,
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
    { label: 'Copiar enlace', icon: '\u{1F517}', action: () => navigator.clipboard.writeText(mr.web_url) },
    { label: 'Copiar referencia', icon: '#', action: () => navigator.clipboard.writeText(`${mr.project_path}!${mr.iid}`) },
    { separator: true },
    { label: 'Recargar ramas', icon: '\u21BB', action: () => refresh() },
  ];
  ctxX.value = e.clientX;
  ctxY.value = e.clientY;
  ctxVisible.value = true;
}
</script>

<template>
  <div class="mr-view">
    <!-- Filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        class="filter-tab"
        :class="{ active: mrStore.activeFilter === tab.value }"
        @click="mrStore.activeFilter = tab.value"
      >{{ tab.label }}</button>
    </div>

    <ViewToolbar
      v-model:filter="mrStore.filterText"
      filterPlaceholder="Filtrar MRs por titulo, proyecto, rama o label..."
      showCollapse
      :allExpanded="allExpanded"
      :refreshing="refreshing"
      :loading="mrStore.loading"
      @refresh="refresh"
      @toggleCollapse="toggleCollapseAll"
    >
      <CustomSelect v-model="mrStore.groupBy" :options="[
        { value: 'project', label: 'Por proyecto' },
        { value: 'priority', label: 'Por prioridad' },
        { value: 'none', label: 'Sin agrupar' },
      ]" />
    </ViewToolbar>

    <StatusBanner v-if="mrStore.error" type="error">{{ mrStore.error }}</StatusBanner>
    <LoadingState v-if="mrStore.loading && mrStore.mergeRequests.length === 0" text="Cargando merge requests..." />

    <template v-else>
      <CollapsibleGroup
        v-for="(mrs, project) in mrStore.groupedMRs"
        :key="project"
        :label="String(project)"
        :count="mrs.length"
      >
        <MRTable :merge-requests="mrs" :followedKeys="followedKeys" @select="openMRDetail" @update-score="onUpdateScore" @unfollow="onUnfollow" @contextmenu="onContextMenu" />
      </CollapsibleGroup>

      <EmptyState v-if="mrStore.filteredMRs.length === 0 && !mrStore.loading" text="Sin merge requests que mostrar" />
    </template>

    <MRDetailModal :mr="selectedMR" :open="showDetail" @close="showDetail = false" />

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
