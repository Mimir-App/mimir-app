<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { injectCollapseContext } from '../../composables/useCollapseAll';

const props = withDefaults(defineProps<{
  label: string;
  count?: number;
  summary?: string;
  collapsed?: boolean;
}>(), {
  collapsed: false,
});

const isCollapsed = ref(props.collapsed);
const ctx = injectCollapseContext();
const groupId = `group-${Math.random().toString(36).slice(2, 9)}`;

if (ctx) {
  onMounted(() => ctx.register(groupId, isCollapsed));
  onUnmounted(() => ctx.unregister(groupId));

  watch(ctx.signal, (val) => {
    if (val !== null) {
      isCollapsed.value = val;
    }
  });
}

function toggle() {
  isCollapsed.value = !isCollapsed.value;
}
</script>

<template>
  <div class="collapsible-group" :class="{ collapsed: isCollapsed }">
    <div class="group-header" @click="toggle">
      <span class="toggle-icon">{{ isCollapsed ? '&#x25B6;' : '&#x25BC;' }}</span>
      <h3 class="group-label">
        {{ label }}
        <span v-if="count != null" class="group-count">({{ count }})</span>
      </h3>
      <span v-if="summary" class="group-summary">{{ summary }}</span>
    </div>
    <div v-show="!isCollapsed" class="group-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.collapsible-group {
  margin-bottom: 16px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 4px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  user-select: none;
}

.group-header:hover {
  background: var(--bg-hover);
  border-radius: 4px 4px 0 0;
}

.toggle-icon {
  font-size: 10px;
  color: var(--text-secondary);
  min-width: 14px;
}

.group-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.group-count {
  font-weight: 400;
  font-size: 13px;
}

.group-summary {
  margin-left: auto;
  color: var(--accent);
  font-size: 13px;
  font-weight: 500;
}

.group-content {
  margin-top: 4px;
}
</style>
