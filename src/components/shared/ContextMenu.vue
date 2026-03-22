<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';

export interface SelectOption {
  label: string;
  value: number;
}

export interface MenuItem {
  label: string;
  icon?: string;
  action: () => void;
  separator?: false;
  disabled?: boolean;
  danger?: boolean;
  select?: {
    options: SelectOption[];
    onSelect: (val: number) => void;
  };
}

export interface MenuSeparator {
  separator: true;
}

export type MenuEntry = MenuItem | MenuSeparator;

const props = defineProps<{
  items: MenuEntry[];
  x: number;
  y: number;
}>();

const emit = defineEmits<{ close: [] }>();
const menuEl = ref<HTMLElement | null>(null);

function handleClick(item: MenuEntry) {
  if (item.separator) return;
  if (item.disabled) return;
  if (item.select) return; // handled by select
  item.action();
  emit('close');
}

function handleSelect(item: MenuItem, val: number) {
  if (!item.select) return;
  item.select.onSelect(val);
  emit('close');
}

function handleClickOutside(e: MouseEvent) {
  if (menuEl.value && !menuEl.value.contains(e.target as Node)) {
    emit('close');
  }
}

function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close');
}

onMounted(async () => {
  document.addEventListener('mousedown', handleClickOutside);
  document.addEventListener('keydown', handleEscape);
  await nextTick();
  if (menuEl.value) {
    const rect = menuEl.value.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      menuEl.value.style.left = `${props.x - rect.width}px`;
    }
    if (rect.bottom > window.innerHeight) {
      menuEl.value.style.top = `${props.y - rect.height}px`;
    }
  }
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
  document.removeEventListener('keydown', handleEscape);
});
</script>

<template>
  <Teleport to="body">
    <div
      ref="menuEl"
      class="context-menu"
      :style="{ left: x + 'px', top: y + 'px' }"
    >
      <template v-for="(item, i) in items" :key="i">
        <div v-if="item.separator" class="menu-separator"></div>
        <div v-else-if="item.select" class="menu-item-select">
          <span class="menu-item-label">
            <span v-if="item.icon" class="menu-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </span>
          <div class="select-options">
            <button
              v-for="opt in item.select.options"
              :key="opt.value"
              class="select-chip"
              :class="{ negative: opt.value < 0 }"
              @click="handleSelect(item, opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>
        <button
          v-else
          class="menu-item"
          :class="{ disabled: item.disabled, danger: item.danger }"
          @click="handleClick(item)"
        >
          <span v-if="item.icon" class="menu-icon">{{ item.icon }}</span>
          <span class="menu-label">{{ item.label }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 220px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 14px;
  font-size: 13px;
  color: var(--text-primary);
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.menu-item:hover:not(.disabled) {
  background: var(--bg-hover);
}

.menu-item.disabled {
  opacity: 0.4;
  cursor: default;
}

.menu-item.danger {
  color: var(--error);
}

.menu-item.danger:hover:not(.disabled) {
  background: rgba(241, 76, 76, 0.1);
}

.menu-icon {
  width: 18px;
  text-align: center;
  font-size: 12px;
  flex-shrink: 0;
  opacity: 0.7;
}

.menu-label {
  flex: 1;
  white-space: nowrap;
}

.menu-separator {
  height: 1px;
  background: var(--border);
  margin: 4px 8px;
}

/* Select inline */
.menu-item-select {
  padding: 6px 14px;
}

.menu-item-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.select-options {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.select-chip {
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-card);
  color: var(--success);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.1s;
}

.select-chip:hover {
  border-color: var(--success);
  background: rgba(78, 201, 176, 0.15);
}

.select-chip.negative {
  color: var(--error);
}

.select-chip.negative:hover {
  border-color: var(--error);
  background: rgba(241, 76, 76, 0.1);
}
</style>
