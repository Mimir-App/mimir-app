<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  name: string;
  icon?: string;
  description: string;
  connected: boolean;
  connectLabel?: string;
  disconnectLabel?: string;
  testing?: boolean;
  testResult?: 'ok' | 'fail' | null;
  testMessage?: string;
}>(), {
  testing: false,
  testResult: null,
  testMessage: '',
});

const emit = defineEmits<{
  connect: [];
  disconnect: [];
  edit: [];
  test: [];
}>();

const btnLabel = computed(() => props.connectLabel || `Conectar ${props.name}`);
const dcLabel = computed(() => props.disconnectLabel || 'Desconectar');
</script>

<template>
  <div class="integration-card" :class="{ connected }">
    <!-- Header -->
    <div class="card-header">
      <div class="card-icon" :class="{ connected }">
        <slot name="icon">
          <span class="icon-text">{{ icon }}</span>
        </slot>
      </div>
      <div class="card-info">
        <h3 class="card-name">{{ name }}</h3>
        <p v-if="!connected" class="card-desc">{{ description }}</p>
        <slot v-else name="status" />
      </div>
      <span v-if="connected" class="status-dot" title="Conectado"></span>
    </div>

    <!-- Detalles (solo conectado) -->
    <div v-if="connected" class="card-details">
      <slot name="details" />
    </div>

    <!-- Setup slot (solo desconectado) -->
    <slot v-if="!connected" name="setup" />

    <!-- Footer con acciones -->
    <div class="card-footer">
      <template v-if="connected">
        <button type="button" class="btn btn-sm btn-secondary" @click="emit('edit')">
          Editar
        </button>
        <button type="button" class="btn btn-sm btn-secondary" @click="emit('test')" :disabled="testing">
          {{ testing ? 'Comprobando...' : 'Comprobar' }}
        </button>
        <span v-if="testResult === 'ok'" class="test-ok">{{ testMessage || 'OK' }}</span>
        <span v-else-if="testResult === 'fail'" class="test-fail">{{ testMessage || 'Error' }}</span>
        <div class="spacer"></div>
        <button type="button" class="btn btn-sm btn-danger" @click="emit('disconnect')">
          {{ dcLabel }}
        </button>
      </template>
      <template v-else>
        <button type="button" class="btn btn-primary" @click="emit('connect')">
          {{ btnLabel }}
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.integration-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  transition: border-color 0.15s;
}

.integration-card.connected {
  border-color: var(--success);
  border-left: 3px solid var(--success);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.card-icon.connected {
  background: var(--success-soft);
}

.icon-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  flex-shrink: 0;
}

.card-details {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.spacer {
  flex: 1;
}

.test-ok { color: var(--success); font-size: 12px; }
.test-fail { color: var(--error); font-size: 12px; }

.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn-sm { padding: 6px 14px; font-size: 12px; }
.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-hover); border-color: var(--text-secondary); }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: var(--error-soft); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
