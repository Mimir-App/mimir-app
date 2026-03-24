<script setup lang="ts">
import { Inbox } from 'lucide-vue-next';

withDefaults(defineProps<{
  text?: string;
  subtitle?: string;
  icon?: any;
}>(), {
  text: 'Sin datos que mostrar',
  subtitle: '',
});
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">
      <component :is="icon ?? Inbox" :size="36" :stroke-width="1.25" />
    </div>
    <p class="empty-text">{{ text }}</p>
    <p v-if="subtitle" class="empty-subtitle">{{ subtitle }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
}

.empty-icon {
  color: var(--text-muted);
  opacity: 0.6;
  margin-bottom: var(--space-1);
}

.empty-text {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
}

.empty-subtitle {
  color: var(--text-muted);
  font-size: var(--text-xs);
  max-width: 280px;
  text-align: center;
  line-height: 1.5;
}

.empty-action {
  margin-top: var(--space-3);
}
</style>
