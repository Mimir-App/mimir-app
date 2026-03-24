<script setup lang="ts">
import { computed } from 'vue';
import type { BlockStatus } from '../../lib/types';

const props = defineProps<{
  status: BlockStatus;
  error?: string | null;
}>();

const config = computed(() => {
  const map: Record<BlockStatus, { label: string; cls: string }> = {
    auto: { label: 'Auto', cls: 'auto' },
    closed: { label: 'Cerrado', cls: 'closed' },
    confirmed: { label: 'Confirmado', cls: 'confirmed' },
    synced: { label: 'Enviado', cls: 'synced' },
    error: { label: 'Error', cls: 'error' },
  };
  return map[props.status] ?? { label: props.status, cls: 'auto' };
});

const tooltip = computed(() => {
  if (props.status === 'error' && props.error) {
    return `Error: ${props.error}`;
  }
  return undefined;
});
</script>

<template>
  <span class="sync-badge" :class="config.cls" :title="tooltip">{{ config.label }}</span>
</template>

<style scoped>
.sync-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 500;
  cursor: default;
}

.sync-badge.auto,
.sync-badge.closed {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.sync-badge.confirmed {
  background: var(--info-soft);
  color: #569cd6;
}

.sync-badge.synced {
  background: var(--success-soft);
  color: var(--success);
}

.sync-badge.error {
  background: var(--error-soft);
  color: var(--error);
  cursor: help;
}
</style>
