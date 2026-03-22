<script setup lang="ts">
import FilterBar from './FilterBar.vue';
import { RefreshCw, ChevronsUpDown } from 'lucide-vue-next';

withDefaults(defineProps<{
  filterPlaceholder?: string;
  showFilter?: boolean;
  showCollapse?: boolean;
  showRefresh?: boolean;
  refreshing?: boolean;
  loading?: boolean;
  allExpanded?: boolean;
}>(), {
  showFilter: true,
  showCollapse: false,
  showRefresh: true,
  refreshing: false,
  loading: false,
  allExpanded: true,
});

const filterText = defineModel<string>('filter', { default: '' });
const emit = defineEmits<{ refresh: []; toggleCollapse: [] }>();
</script>

<template>
  <div class="view-toolbar">
    <div v-if="showFilter" class="toolbar-filter">
      <FilterBar
        v-model="filterText"
        :placeholder="filterPlaceholder ?? 'Filtrar...'"
      />
    </div>

    <!-- Slot para widgets extra (selects de agrupacion, fechas, etc.) -->
    <div class="toolbar-widgets">
      <slot />
    </div>

    <button
      v-if="showCollapse"
      class="btn btn-ghost btn-collapse"
      @click="emit('toggleCollapse')"
    >
      <ChevronsUpDown :size="14" :stroke-width="2" />
      {{ allExpanded ? 'Colapsar' : 'Expandir' }}
    </button>

    <button
      v-if="showRefresh"
      class="btn btn-ghost btn-icon"
      @click="emit('refresh')"
      :disabled="refreshing || loading"
      title="Refrescar"
    >
      <RefreshCw :size="15" :stroke-width="2" :class="{ spinning: refreshing }" />
    </button>
  </div>
</template>

<style scoped>
.view-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.toolbar-filter {
  flex: 1;
  min-width: 150px;
}

.toolbar-filter :deep(.filter-bar) {
  margin-bottom: 0;
}

.toolbar-widgets {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.toolbar-widgets :deep(.custom-select) {
  width: 160px;
}

.btn {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: transparent;
  color: var(--text-secondary);
  padding: var(--space-2);
  font-size: var(--text-sm);
}

.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.btn-icon {
  padding: 6px;
  border-radius: var(--radius-md);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 1s linear infinite;
}
</style>
