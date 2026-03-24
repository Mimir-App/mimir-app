<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
  text: string;
}>();

const visible = ref(false);
</script>

<template>
  <span
    class="help-tooltip"
    @mouseenter="visible = true"
    @mouseleave="visible = false"
  >
    <span class="help-icon">?</span>
    <Transition name="tooltip">
      <span v-if="visible" class="tooltip-content">{{ text }}</span>
    </Transition>
  </span>
</template>

<style scoped>
.help-tooltip {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}

.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
  cursor: help;
  transition: all 0.15s;
}

.help-icon:hover {
  background: var(--accent);
  color: white;
}

.tooltip-content {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  white-space: normal;
  width: max-content;
  max-width: 280px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: var(--z-sticky);
  pointer-events: none;
}

.tooltip-content::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--border);
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}
</style>
