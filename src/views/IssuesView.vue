<script setup lang="ts">
import { onMounted } from 'vue';
import { useIssuesStore } from '../stores/issues';
import FilterBar from '../components/shared/FilterBar.vue';
import IssueTable from '../components/issues/IssueTable.vue';

const issuesStore = useIssuesStore();

onMounted(() => {
  issuesStore.fetchIssues();
});
</script>

<template>
  <div class="issues-view">
    <FilterBar
      v-model="issuesStore.filterText"
      placeholder="Filtrar issues por título, proyecto o label..."
    />

    <div v-if="issuesStore.error" class="error-banner">
      {{ issuesStore.error }}
    </div>

    <div v-if="issuesStore.loading" class="loading">Cargando issues...</div>

    <template v-else>
      <div
        v-for="(issues, project) in issuesStore.groupedIssues"
        :key="project"
        class="project-group"
      >
        <h3 class="project-name">{{ project }} ({{ issues.length }})</h3>
        <IssueTable :issues="issues" />
      </div>

      <div v-if="issuesStore.filteredIssues.length === 0" class="empty-state">
        Sin issues que mostrar
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
