<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import BlockTable from '../components/blocks/BlockTable.vue';

const blocksStore = useBlocksStore();

onMounted(() => {
  blocksStore.fetchBlocks();
});

watch(() => blocksStore.selectedDate, () => {
  blocksStore.fetchBlocks();
});

function confirmAll() {
  const pending = blocksStore.blocks.filter(b => b.status === 'auto');
  pending.forEach(b => blocksStore.confirmBlock(b.id));
}
</script>

<template>
  <div class="review-day">
    <div class="review-toolbar">
      <input
        type="date"
        v-model="blocksStore.selectedDate"
        class="date-picker"
      />
      <div class="toolbar-stats">
        <span>{{ blocksStore.blocks.length }} bloques</span>
        <span class="separator">|</span>
        <span>{{ blocksStore.totalHoursToday.toFixed(1) }}h total</span>
      </div>
      <div class="toolbar-actions">
        <button
          class="btn btn-secondary"
          @click="confirmAll"
          :disabled="blocksStore.pendingBlocks.length === 0"
        >
          Confirmar todos
        </button>
        <button
          class="btn btn-primary"
          @click="blocksStore.syncToOdoo()"
          :disabled="blocksStore.blocks.filter(b => b.status === 'confirmed').length === 0"
        >
          Enviar a Odoo
        </button>
      </div>
    </div>

    <div v-if="blocksStore.error" class="error-banner">
      {{ blocksStore.error }}
    </div>

    <div v-if="blocksStore.loading" class="loading">Cargando bloques...</div>

    <BlockTable v-else :blocks="blocksStore.blocks" />
  </div>
</template>

<style scoped>
.review-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.date-picker {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
}

.toolbar-stats {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.separator {
  margin: 0 6px;
  color: var(--border);
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.error-banner {
  padding: 10px 14px;
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  border-radius: 4px;
  color: var(--error);
  font-size: 13px;
  margin-bottom: 12px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
