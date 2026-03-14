<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useIssuesStore } from '../stores/issues';
import { useConfigStore } from '../stores/config';
import FilterBar from '../components/shared/FilterBar.vue';
import CollapsibleGroup from '../components/shared/CollapsibleGroup.vue';
import IssueTable from '../components/issues/IssueTable.vue';

const issuesStore = useIssuesStore();
const configStore = useConfigStore();
const refreshing = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  issuesStore.fetchIssues();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

function startPolling() {
  stopPolling();
  const interval = (configStore.config.refresh_interval_seconds || 300) * 1000;
  pollTimer = setInterval(() => {
    issuesStore.fetchIssues();
  }, interval);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    await issuesStore.fetchIssues();
  } finally {
    refreshing.value = false;
  }
}
</script>

<template>
  <div class="issues-view">
    <div class="view-toolbar">
      <FilterBar
        v-model="issuesStore.filterText"
        placeholder="Filtrar issues por titulo, proyecto o label..."
      />
      <button
        class="btn btn-ghost"
        @click="refresh"
        :disabled="refreshing || issuesStore.loading"
        title="Refrescar"
      >
        &#x21bb;
      </button>
    </div>

    <div v-if="issuesStore.error" class="error-banner">
      {{ issuesStore.error }}
    </div>

    <div v-if="issuesStore.loading && issuesStore.issues.length === 0" class="loading">
      Cargando issues...
    </div>

    <template v-else>
      <CollapsibleGroup
        v-for="(issues, project) in issuesStore.groupedIssues"
        :key="project"
        :label="String(project)"
        :count="issues.length"
      >
        <IssueTable :issues="issues" />
      </CollapsibleGroup>

      <div v-if="issuesStore.filteredIssues.length === 0 && !issuesStore.loading" class="empty-state">
        Sin issues que mostrar
      </div>
    </template>
  </div>
</template>

<style scoped>
.view-toolbar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}

.project-group {
  margin-bottom: 20px;
}

.project-name {
  font-size: 14px;
  font-weight: 600;
  padding: 8px 0;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
}

.error-banner {
  padding: 10px 14px;
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  border-radius: 4px;
  color: var(--error);
  font-size: 13px;
  margin-bottom: 12px;
}

.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.btn {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  padding: 6px 10px;
}

.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
}
</style>
