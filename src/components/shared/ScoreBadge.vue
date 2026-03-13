<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ score: number }>();

const level = computed(() => {
  if (props.score >= 150) return 'critical';
  if (props.score >= 100) return 'high';
  if (props.score >= 50) return 'medium';
  return 'low';
});
</script>

<template>
  <span class="score-badge" :class="level">{{ score }}</span>
</template>

<style scoped>
.score-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.score-badge.critical {
  background: rgba(241, 76, 76, 0.2);
  color: var(--error);
}

.score-badge.high {
  background: rgba(220, 220, 170, 0.2);
  color: var(--warning);
}

.score-badge.medium {
  background: rgba(86, 156, 214, 0.2);
  color: var(--accent);
}

.score-badge.low {
  background: var(--bg-card);
  color: var(--text-secondary);
}
</style>
