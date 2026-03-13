<script setup lang="ts">
const model = defineModel<string>({ default: '' });

defineProps<{
  placeholder?: string;
}>();
</script>

<template>
  <div class="filter-bar">
    <input
      type="text"
      v-model="model"
      :placeholder="placeholder ?? 'Filtrar...'"
      class="filter-input"
    />
    <button v-if="model" class="clear-btn" @click="model = ''">×</button>
  </div>
</template>

<style scoped>
.filter-bar {
  position: relative;
  margin-bottom: 12px;
}

.filter-input {
  width: 100%;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 32px 8px 12px;
  font-size: 13px;
}

.filter-input::placeholder {
  color: var(--text-secondary);
}

.filter-input:focus {
  outline: none;
  border-color: var(--accent);
}

.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}

.clear-btn:hover {
  color: var(--text-primary);
}
</style>
