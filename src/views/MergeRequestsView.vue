<script setup lang="ts">
import { onMounted } from 'vue';
import { useMergeRequestsStore } from '../stores/merge_requests';
import FilterBar from '../components/shared/FilterBar.vue';
import MRTable from '../components/merge_requests/MRTable.vue';

const mrStore = useMergeRequestsStore();

onMounted(() => {
  mrStore.fetchMergeRequests();
});
</script>

<template>
  <div class="mr-view">
    <FilterBar
      v-model="mrStore.filterText"
      placeholder="Filtrar MRs por título, proyecto o rama..."
    />

    <div v-if="mrStore.error" class="error-banner">
      {{ mrStore.error }}
    </div>

    <div v-if="mrStore.loading" class="loading">Cargando merge requests...</div>

    <template v-else>
      <div
        v-for="(mrs, project) in mrStore.groupedMRs"
        :key="project"
        class="project-group"
      >
        <h3 class="project-name">{{ project }} ({{ mrs.length }})</h3>
        <MRTable :merge-requests="mrs" />
      </div>

      <div v-if="mrStore.filteredMRs.length === 0" class="empty-state">
        Sin merge requests que mostrar
      </div>
    </template>
  </div>
</template>

<style scoped>
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
</style>
