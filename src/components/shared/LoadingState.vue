<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next';

withDefaults(defineProps<{
  text?: string;
}>(), {
  text: 'Cargando...',
});
</script>

<template>
  <div class="loading-state" role="status" aria-live="polite">
    <Loader2 class="loading-spinner" :size="24" :stroke-width="2" />
    <span>{{ text }}</span>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.loading-spinner {
  color: var(--accent);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
