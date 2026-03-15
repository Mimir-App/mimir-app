<script setup lang="ts">
import FilterBar from './FilterBar.vue';

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
      <span class="collapse-icon">{{ allExpanded ? '&#x25B6;' : '&#x25BC;' }}</span>
      {{ allExpanded ? 'Collapse all' : 'Expand all' }}
    </button>

    <button
      v-if="showRefresh"
      class="btn btn-ghost"
      @click="emit('refresh')"
      :disabled="refreshing || loading"
      title="Refrescar"
    >
      &#x21bb;
    </button>
  </div>
</template>

<style scoped>
.view-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
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
  gap: 10px;
  flex-shrink: 0;
}

.toolbar-widgets :deep(.custom-select) {
  width: 160px;
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
