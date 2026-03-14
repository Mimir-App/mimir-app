<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useMergeRequestsStore } from '../stores/merge_requests';
import { useConfigStore } from '../stores/config';
import FilterBar from '../components/shared/FilterBar.vue';
import MRTable from '../components/merge_requests/MRTable.vue';

const mrStore = useMergeRequestsStore();
const configStore = useConfigStore();
const refreshing = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  mrStore.fetchMergeRequests();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

function startPolling() {
  stopPolling();
  const interval = (configStore.config.refresh_interval_seconds || 300) * 1000;
  pollTimer = setInterval(() => {
    mrStore.fetchMergeRequests();
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
    await mrStore.fetchMergeRequests();
  } finally {
    refreshing.value = false;
  }
}
</script>

<template>
  <div class="mr-view">
    <div class="view-toolbar">
      <FilterBar
        v-model="mrStore.filterText"
        placeholder="Filtrar MRs por titulo, proyecto o rama..."
      />
      <button
        class="btn btn-ghost"
        @click="refresh"
        :disabled="refreshing || mrStore.loading"
        title="Refrescar"
      >
        &#x21bb;
      </button>
    </div>

    <div v-if="mrStore.error" class="error-banner">
      {{ mrStore.error }}
    </div>

    <div v-if="mrStore.loading && mrStore.mergeRequests.length === 0" class="loading">
      Cargando merge requests...
    </div>

    <template v-else>
      <div
        v-for="(mrs, project) in mrStore.groupedMRs"
        :key="project"
        class="project-group"
      >
        <h3 class="project-name">{{ project }} ({{ mrs.length }})</h3>
        <MRTable :merge-requests="mrs" />
      </div>

      <div v-if="mrStore.filteredMRs.length === 0 && !mrStore.loading" class="empty-state">
        Sin merge requests que mostrar
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
