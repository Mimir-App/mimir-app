<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ confidence: number }>();

const label = computed(() => {
  if (props.confidence >= 0.8) return 'Alta';
  if (props.confidence >= 0.5) return 'Media';
  return 'Baja';
});

const level = computed(() => {
  if (props.confidence >= 0.8) return 'high';
  if (props.confidence >= 0.5) return 'medium';
  return 'low';
});
</script>

<template>
  <span class="confidence-badge" :class="level" :title="`Confianza: ${(confidence * 100).toFixed(0)}%`">
    {{ label }}
  </span>
</template>

<style scoped>
.confidence-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.confidence-badge.high {
  background: var(--success-soft);
  color: var(--success);
}

.confidence-badge.medium {
  background: var(--warning-soft);
  color: var(--warning);
}

.confidence-badge.low {
  background: var(--error-soft);
  color: var(--error);
}
</style>
