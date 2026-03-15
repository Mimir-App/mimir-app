<script setup lang="ts">
import { ref } from 'vue';
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

const issuesStore = useIssuesStore();
const refreshing = ref(false);
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
usePolling(() => issuesStore.fetchIssues());

async function refresh() {
  refreshing.value = true;
  try { await issuesStore.fetchIssues(); } finally { refreshing.value = false; }
}
</script>

<template>
  <div class="issues-view">
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
        <IssueTable :issues="issues" />
      </CollapsibleGroup>

      <EmptyState v-if="issuesStore.filteredIssues.length === 0 && !issuesStore.loading" text="Sin issues que mostrar" />
    </template>
  </div>
</template>
