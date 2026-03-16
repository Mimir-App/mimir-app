<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  name: string;
  icon: string;
  description: string;
  connected: boolean;
  connectLabel?: string;
  disconnectLabel?: string;
}>();

const emit = defineEmits<{
  connect: [];
  disconnect: [];
}>();

const btnLabel = computed(() => props.connectLabel || `Conectar ${props.name}`);
const dcLabel = computed(() => props.disconnectLabel || 'Cerrar sesion');
</script>

<template>
  <div class="integration-card">
    <!-- No conectado -->
    <div v-if="!connected" class="integration-login">
      <div class="integration-icon">{{ icon }}</div>
      <h3>{{ name }}</h3>
      <p class="integration-desc">{{ description }}</p>
      <slot name="setup" />
      <button
        type="button"
        class="btn btn-primary integration-connect-btn"
        @click="emit('connect')"
      >
        {{ btnLabel }}
      </button>
    </div>

    <!-- Conectado -->
    <div v-else class="integration-session">
      <div class="integration-session-header">
        <div class="integration-icon connected">{{ icon }}</div>
        <div>
          <h3>{{ name }}</h3>
          <slot name="status" />
        </div>
      </div>
      <slot name="details" />
      <div class="integration-actions">
        <button type="button" class="btn btn-danger btn-sm" @click="emit('disconnect')">
          {{ dcLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.integration-login { display: flex; flex-direction: column; align-items: center; padding: 24px 0; max-width: 480px; margin: 0 auto; text-align: center; }
.integration-login h3 { margin: 12px 0 8px; }
.integration-desc { color: var(--text-secondary); font-size: 13px; margin-bottom: 16px; }
.integration-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; color: var(--accent); }
.integration-icon.connected { background: var(--success); color: white; }
.integration-connect-btn { margin-top: 16px; padding: 12px 32px; font-size: 15px; }
.integration-session { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
.integration-session-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.integration-session-header h3 { margin: 0; }
.integration-actions { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
