<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { injectCollapseContext } from '../../composables/useCollapseAll';
import { ChevronRight } from 'lucide-vue-next';

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
    <button
      class="group-header"
      @click="toggle"
      :aria-expanded="!isCollapsed"
      :aria-label="`${label}${count != null ? ` (${count})` : ''}`"
    >
      <ChevronRight class="toggle-icon" :class="{ expanded: !isCollapsed }" :size="14" :stroke-width="2" aria-hidden="true" />
      <h3 class="group-label">
        {{ label }}
        <span v-if="count != null" class="group-count">({{ count }})</span>
      </h3>
      <span v-if="summary" class="group-summary">{{ summary }}</span>
    </button>
    <div v-show="!isCollapsed" class="group-content" role="region">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.collapsible-group {
  margin-bottom: var(--space-4);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-2) var(--space-1);
  cursor: pointer;
  border: none;
  background: none;
  border-bottom: 1px solid var(--border);
  user-select: none;
  width: 100%;
  text-align: left;
  color: inherit;
  font-family: inherit;
  transition: background var(--duration-fast) var(--ease-out);
}

.group-header:hover {
  background: var(--bg-hover);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.toggle-icon {
  color: var(--text-secondary);
  flex-shrink: 0;
  transition: transform var(--duration-base) var(--ease-out);
}

.toggle-icon.expanded {
  transform: rotate(90deg);
}

.group-label {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.group-count {
  font-weight: 400;
  font-size: var(--text-sm);
}

.group-summary {
  margin-left: auto;
  color: var(--accent);
  font-size: var(--text-sm);
  font-weight: 500;
}

.group-content {
  margin-top: var(--space-1);
}
</style>
