<script setup lang="ts">
import { computed } from 'vue';
import type { BlockStatus } from '../../lib/types';

const props = defineProps<{ status: BlockStatus }>();

const config = computed(() => {
  const map: Record<BlockStatus, { label: string; cls: string }> = {
    auto: { label: 'Auto', cls: 'auto' },
    confirmed: { label: 'Confirmado', cls: 'confirmed' },
    synced: { label: 'Enviado', cls: 'synced' },
    error: { label: 'Error', cls: 'error' },
  };
  return map[props.status];
});
</script>

<template>
  <span class="sync-badge" :class="config.cls">{{ config.label }}</span>
</template>

<style scoped>
.sync-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 500;
}

.sync-badge.auto {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.sync-badge.confirmed {
  background: rgba(86, 156, 214, 0.15);
  color: var(--accent);
}

.sync-badge.synced {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
}

.sync-badge.error {
  background: rgba(241, 76, 76, 0.15);
  color: var(--error);
}
</style>
