<script setup lang="ts">
import ModalDialog from '../shared/ModalDialog.vue';
import { getAllWidgetDefs } from '../../lib/widget-registry';

defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  add: [type: string];
}>();

const widgetDefs = getAllWidgetDefs();
</script>

<template>
  <ModalDialog title="Anadir widget" :open="open" @close="emit('close')">
    <div class="gallery">
      <div
        v-for="def in widgetDefs"
        :key="def.type"
        class="gallery-item"
      >
        <span class="widget-icon">{{ def.icon }}</span>
        <div class="widget-info">
          <span class="widget-name">
            {{ def.name }}
            <span v-if="def.comingSoon" class="badge-coming-soon">Proximamente</span>
          </span>
          <span class="widget-desc">{{ def.description }}</span>
        </div>
        <button
          class="btn-add"
          :class="{ 'btn-add--disabled': def.comingSoon }"
          :disabled="def.comingSoon"
          @click="!def.comingSoon && emit('add', def.type)"
        >Anadir</button>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.gallery {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gallery-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: border-color 0.15s;
}

.gallery-item:hover {
  border-color: var(--accent);
}

.widget-icon {
  font-size: 22px;
  width: 32px;
  text-align: center;
  flex-shrink: 0;
}

.widget-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.widget-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.widget-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-add {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 5px;
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}

.btn-add:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-add--disabled {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  cursor: not-allowed;
  opacity: 0.6;
}

.badge-coming-soon {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
  vertical-align: middle;
}
</style>
