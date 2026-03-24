<script setup lang="ts">
import { AlertTriangle, CheckCircle2, XCircle, Info, X } from 'lucide-vue-next';

withDefaults(defineProps<{
  type: 'success' | 'error' | 'warning' | 'info';
  dismissible?: boolean;
}>(), {
  dismissible: false,
});

const emit = defineEmits<{ dismiss: [] }>();

const iconMap = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};
</script>

<template>
  <div class="banner" :class="type" :role="type === 'error' ? 'alert' : 'status'" aria-live="polite">
    <div class="banner-content">
      <component :is="iconMap[type]" class="banner-icon" :size="15" :stroke-width="2" aria-hidden="true" />
      <span class="banner-text"><slot /></span>
    </div>
    <button v-if="dismissible" class="banner-close" @click="emit('dismiss')" aria-label="Cerrar">
      <X :size="14" :stroke-width="2" />
    </button>
  </div>
</template>

<style scoped>
.banner {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  margin-bottom: var(--space-3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid transparent;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
}

.banner-icon {
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
}

.banner.error {
  background: var(--error-soft);
  border-color: var(--error);
  color: var(--error);
}

.banner.success {
  background: var(--success-soft);
  border-color: var(--success);
  color: var(--success);
}

.banner.warning {
  background: var(--warning-soft);
  border-color: var(--warning);
  color: var(--warning);
}

.banner.info {
  background: var(--info-soft);
  border-color: var(--info);
  color: var(--info);
}

.banner-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  opacity: 0.7;
  transition: opacity var(--duration-fast);
}

.banner-close:hover {
  opacity: 1;
}
</style>
