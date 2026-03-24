<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ChevronDown } from 'lucide-vue-next';

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
const highlightIndex = ref(-1);

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
  if (open.value) {
    search.value = '';
    highlightIndex.value = filteredOptions.value.findIndex(o => o.value === props.modelValue);
  }
}

function select(value: string | number | null) {
  emit('update:modelValue', value);
  open.value = false;
}

function handleKeydown(e: KeyboardEvent) {
  if (!open.value) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open.value = true;
      search.value = '';
      highlightIndex.value = filteredOptions.value.findIndex(o => o.value === props.modelValue);
      return;
    }
    return;
  }

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      highlightIndex.value = Math.min(highlightIndex.value + 1, filteredOptions.value.length - 1);
      break;
    case 'ArrowUp':
      e.preventDefault();
      highlightIndex.value = Math.max(highlightIndex.value - 1, 0);
      break;
    case 'Enter':
      e.preventDefault();
      if (highlightIndex.value >= 0 && highlightIndex.value < filteredOptions.value.length) {
        select(filteredOptions.value[highlightIndex.value].value);
      }
      break;
    case 'Escape':
      e.preventDefault();
      open.value = false;
      break;
    case 'Home':
      e.preventDefault();
      highlightIndex.value = 0;
      break;
    case 'End':
      e.preventDefault();
      highlightIndex.value = filteredOptions.value.length - 1;
      break;
  }
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
  <div class="custom-select" ref="el" :class="{ open, disabled }" @keydown="handleKeydown">
    <button
      type="button"
      class="select-trigger"
      @click="toggle"
      role="combobox"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :aria-label="selectedLabel"
    >
      <span class="select-label" :class="{ placeholder: isPlaceholder }">{{ selectedLabel }}</span>
      <ChevronDown class="select-arrow" :class="{ flipped: open }" :size="14" :stroke-width="2" />
    </button>
    <Transition name="dropdown">
      <div v-if="open" class="select-dropdown">
        <input
          v-if="searchable"
          type="text"
          v-model="search"
          class="select-search"
          placeholder="Buscar..."
          aria-label="Buscar opciones"
          @click.stop
          @input="highlightIndex = 0"
        />
        <div class="select-options" role="listbox">
          <button
            v-for="(opt, idx) in filteredOptions"
            :key="String(opt.value)"
            type="button"
            class="select-option"
            :class="{ active: opt.value === modelValue, highlighted: idx === highlightIndex }"
            role="option"
            :aria-selected="opt.value === modelValue"
            @click="select(opt.value)"
            @mouseenter="highlightIndex = idx"
          >
            <span class="option-label">{{ opt.label }}</span>
            <span v-if="opt.hint" class="option-hint">{{ opt.hint }}</span>
            <span v-if="opt.value === modelValue" class="option-check" aria-hidden="true">&#x2713;</span>
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
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out);
}

.select-trigger:hover {
  border-color: var(--accent);
}

.custom-select.open .select-trigger {
  border-color: var(--accent);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
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
  color: var(--text-secondary);
  margin-left: var(--space-2);
  flex-shrink: 0;
  transition: transform var(--duration-fast) var(--ease-out);
}

.select-arrow.flipped {
  transform: rotate(180deg);
}

.select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: var(--z-dropdown);
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-top: none;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.select-search {
  width: 100%;
  padding: 6px 10px;
  border: none;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-xs);
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
  padding: var(--space-2) var(--space-3);
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  transition: background var(--duration-fast);
  gap: var(--space-2);
}

.select-option:hover,
.select-option.highlighted {
  background: var(--bg-hover);
}

.select-option.active {
  color: var(--accent);
}

.option-label {
  flex: 1;
}

.option-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.option-check {
  font-size: var(--text-xs);
  color: var(--accent);
  flex-shrink: 0;
}

.select-empty {
  padding: var(--space-3);
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity var(--duration-fast), transform var(--duration-fast);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
