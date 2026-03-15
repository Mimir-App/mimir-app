<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = withDefaults(defineProps<{
  modelValue: string | number | null;
  options: { value: string | number | null; label: string; hint?: string }[];
  placeholder?: string;
  disabled?: boolean;
  searchable?: boolean;
}>(), {
  placeholder: '-- Seleccionar --',
  disabled: false,
  searchable: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null];
}>();

const open = ref(false);
const search = ref('');
const el = ref<HTMLElement | null>(null);

const selectedLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue);
  return opt?.label ?? props.placeholder;
});

const isPlaceholder = computed(() => {
  return !props.options.some(o => o.value === props.modelValue);
});

const filteredOptions = computed(() => {
  if (!props.searchable || !search.value) return props.options;
  const q = search.value.toLowerCase();
  return props.options.filter(o => o.label.toLowerCase().includes(q));
});

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) search.value = '';
}

function select(value: string | number | null) {
  emit('update:modelValue', value);
  open.value = false;
}

function handleClickOutside(e: MouseEvent) {
  if (el.value && !el.value.contains(e.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside));
onUnmounted(() => document.removeEventListener('click', handleClickOutside));
</script>

<template>
  <div class="custom-select" ref="el" :class="{ open, disabled }">
    <button type="button" class="select-trigger" @click="toggle">
      <span class="select-label" :class="{ placeholder: isPlaceholder }">{{ selectedLabel }}</span>
      <span class="select-arrow">{{ open ? '&#x25B2;' : '&#x25BC;' }}</span>
    </button>
    <Transition name="dropdown">
      <div v-if="open" class="select-dropdown">
        <input
          v-if="searchable"
          type="text"
          v-model="search"
          class="select-search"
          placeholder="Buscar..."
          @click.stop
        />
        <div class="select-options">
          <button
            v-for="opt in filteredOptions"
            :key="String(opt.value)"
            type="button"
            class="select-option"
            :class="{ active: opt.value === modelValue }"
            @click="select(opt.value)"
          >
            <span class="option-label">{{ opt.label }}</span>
            <span v-if="opt.hint" class="option-hint">{{ opt.hint }}</span>
            <span v-if="opt.value === modelValue" class="option-check">&#x2713;</span>
          </button>
          <div v-if="filteredOptions.length === 0" class="select-empty">Sin resultados</div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.custom-select {
  position: relative;
  width: 100%;
}

.custom-select.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 10px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s;
}

.select-trigger:hover {
  border-color: var(--accent);
}

.custom-select.open .select-trigger {
  border-color: var(--accent);
  border-radius: 4px 4px 0 0;
}

.select-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-label.placeholder {
  color: var(--text-secondary);
}

.select-arrow {
  font-size: 8px;
  color: var(--text-secondary);
  margin-left: 8px;
  flex-shrink: 0;
}

.select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.select-search {
  width: 100%;
  padding: 6px 10px;
  border: none;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 12px;
  font-family: inherit;
  outline: none;
}

.select-options {
  max-height: 220px;
  overflow-y: auto;
}

.select-option {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 10px;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
  gap: 8px;
}

.select-option:hover {
  background: var(--bg-hover);
}

.select-option.active {
  color: var(--accent);
}

.option-label {
  flex: 1;
}

.option-hint {
  font-size: 11px;
  color: var(--text-secondary);
}

.option-check {
  font-size: 12px;
  color: var(--accent);
  flex-shrink: 0;
}

.select-empty {
  padding: 10px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
