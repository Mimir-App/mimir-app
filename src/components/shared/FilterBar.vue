<script setup lang="ts">
import { Search, X } from 'lucide-vue-next';

const model = defineModel<string>({ default: '' });

defineProps<{
  placeholder?: string;
}>();
</script>

<template>
  <div class="filter-bar" role="search">
    <Search class="filter-icon" :size="14" :stroke-width="2" aria-hidden="true" />
    <input
      type="text"
      v-model="model"
      :placeholder="placeholder ?? 'Filtrar...'"
      class="filter-input"
      aria-label="Filtrar contenido"
    />
    <button v-if="model" class="clear-btn" @click="model = ''" aria-label="Limpiar filtro">
      <X :size="14" :stroke-width="2" />
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  position: relative;
  margin-bottom: var(--space-3);
}

.filter-icon {
  position: absolute;
  left: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.filter-input {
  width: 100%;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-8) var(--space-2) 36px;
  font-size: var(--text-sm);
  transition: border-color var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}

.filter-input::placeholder {
  color: var(--text-muted);
}

.filter-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.clear-btn {
  position: absolute;
  right: var(--space-2);
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  transition: all var(--duration-fast);
}

.clear-btn:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
</style>
