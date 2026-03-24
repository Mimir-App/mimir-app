<script setup lang="ts">
import HelpTooltip from '../shared/HelpTooltip.vue';

defineProps<{
  label: string;
  help?: string;
  fullWidth?: boolean;
}>();
</script>

<template>
  <div class="setting-row">
    <label class="setting-row-label">
      {{ label }}
      <HelpTooltip v-if="help" :text="help" />
    </label>
    <div class="setting-row-control" :class="{ 'full-width': fullWidth }">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.setting-row-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  min-width: 120px;
}

.setting-row-control {
  flex: 1;
  max-width: 400px;
}

.setting-row-control.full-width {
  max-width: none;
}
</style>
