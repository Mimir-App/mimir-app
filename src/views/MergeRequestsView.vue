<script setup lang="ts">
import { ref } from 'vue';
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

const mrStore = useMergeRequestsStore();
const refreshing = ref(false);
const { allExpanded, toggle: toggleCollapseAll } = provideCollapseAll();
usePolling(() => mrStore.fetchMergeRequests());

async function refresh() {
  refreshing.value = true;
  try { await mrStore.fetchMergeRequests(); } finally { refreshing.value = false; }
}
</script>

<template>
  <div class="mr-view">
    <ViewToolbar
      v-model:filter="mrStore.filterText"
      filterPlaceholder="Filtrar MRs por titulo, proyecto o rama..."
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
        <MRTable :merge-requests="mrs" />
      </CollapsibleGroup>

      <EmptyState v-if="mrStore.filteredMRs.length === 0 && !mrStore.loading" text="Sin merge requests que mostrar" />
    </template>
  </div>
</template>
