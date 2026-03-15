<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

export interface DashboardWidget {
  id: string;
  label: string;
  span: 1 | 2 | 3;
  rowSpan?: 1 | 2 | 3;
}

const props = defineProps<{
  widgets: DashboardWidget[];
  order: string[];
  spans: Record<string, [number, number]>;
  editing: boolean;
}>();

const emit = defineEmits<{
  'update:order': [order: string[]];
  'update:spans': [spans: Record<string, [number, number]>];
}>();

const dragId = ref<string | null>(null);
const dragOverId = ref<string | null>(null);
const menuId = ref<string | null>(null);
const gridEl = ref<HTMLElement | null>(null);

function getCols(w: DashboardWidget): number {
  return props.spans[w.id]?.[1] ?? w.span;
}

function getRows(w: DashboardWidget): number {
  return props.spans[w.id]?.[0] ?? w.rowSpan ?? 1;
}

const orderedWidgets = computed(() => {
  const ordered: DashboardWidget[] = [];
  for (const id of props.order) {
    const w = props.widgets.find(w => w.id === id);
    if (w) ordered.push(w);
  }
  for (const w of props.widgets) {
    if (!ordered.find(o => o.id === w.id)) ordered.push(w);
  }
  return ordered;
});

function toggleMenu(id: string, e: MouseEvent) {
  e.stopPropagation();
  menuId.value = menuId.value === id ? null : id;
}

function setSize(id: string, rows: number, cols: number) {
  const newSpans = { ...props.spans, [id]: [rows, cols] as [number, number] };
  emit('update:spans', newSpans);
  menuId.value = null;
}

function handleClickOutside() {
  menuId.value = null;
}

onMounted(() => document.addEventListener('click', handleClickOutside));
onUnmounted(() => document.removeEventListener('click', handleClickOutside));

function onDragStart(e: DragEvent, id: string) {
  if (!props.editing) return;
  dragId.value = id;
  if (e.dataTransfer) { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', id); }
}
function onDragOver(e: DragEvent, id: string) {
  if (!props.editing) return;
  e.preventDefault(); dragOverId.value = id;
}
function onDragLeave() { dragOverId.value = null; }
function onDrop(e: DragEvent, targetId: string) {
  e.preventDefault(); dragOverId.value = null;
  if (!dragId.value || dragId.value === targetId) { dragId.value = null; return; }
  const order = orderedWidgets.value.map(w => w.id);
  const from = order.indexOf(dragId.value); const to = order.indexOf(targetId);
  if (from === -1 || to === -1) return;
  order.splice(from, 1); order.splice(to, 0, dragId.value);
  emit('update:order', order); dragId.value = null;
}
function onDragEnd() { dragId.value = null; dragOverId.value = null; }
</script>

<template>
  <div class="dashboard-grid" :class="{ editing }" ref="gridEl">
    <div
      v-for="widget in orderedWidgets"
      :key="widget.id"
      class="grid-cell"
      :style="{
        gridColumn: `span ${getCols(widget)}`,
        gridRow: `span ${getRows(widget)}`,
      }"
      :class="{
        'dragging': dragId === widget.id,
        'drag-over': dragOverId === widget.id,
      }"
      :draggable="editing"
      @dragstart="onDragStart($event, widget.id)"
      @dragover="onDragOver($event, widget.id)"
      @dragleave="onDragLeave"
      @drop="onDrop($event, widget.id)"
      @dragend="onDragEnd"
    >
      <!-- Controles solo en modo edicion -->
      <div v-if="editing" class="cell-controls">
        <span class="widget-label">{{ widget.label }}</span>
        <button class="control-btn" @click.stop="toggleMenu(widget.id, $event)" title="Cambiar tamano">
          {{ getRows(widget) }}x{{ getCols(widget) }}
        </button>

        <Transition name="menu">
          <div v-if="menuId === widget.id" class="size-menu" @click.stop>
            <span class="menu-title">Alto x Ancho</span>
            <div class="size-matrix">
              <div v-for="r in 3" :key="'row' + r" class="size-row">
                <button
                  v-for="c in 3" :key="'cell' + r + c"
                  class="size-cell"
                  :class="{ active: getRows(widget) === r && getCols(widget) === c }"
                  @click="setSize(widget.id, r, c)"
                  :title="`${r} x ${c}`"
                >
                  <span class="cell-preview">
                    <span v-for="ci in 3" :key="ci" class="preview-col">
                      <span v-for="ri in 3" :key="ri" class="preview-block" :class="{ filled: ri <= r && ci <= c }"></span>
                    </span>
                  </span>
                  <span class="cell-num">{{ r }}x{{ c }}</span>
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <slot :name="widget.id" />
    </div>
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(120px, auto);
  gap: 16px;
}

.grid-cell {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  position: relative;
  transition: box-shadow 0.15s, opacity 0.15s;
  overflow: hidden;
}

/* Modo edicion */
.editing .grid-cell {
  border-style: dashed;
  cursor: grab;
}

.editing .grid-cell:active {
  cursor: grabbing;
}

.grid-cell.dragging { opacity: 0.4; }
.grid-cell.drag-over { box-shadow: 0 0 0 2px var(--accent); border-color: var(--accent); }

/* Controles */
.cell-controls {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  position: relative;
}

.widget-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex: 1;
}

.control-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
}

.control-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--accent);
}

/* Size menu */
.size-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: 6px;
  padding: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 50;
}

.menu-title {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 6px;
  white-space: nowrap;
}

.size-matrix { display: flex; flex-direction: column; gap: 3px; }
.size-row { display: flex; gap: 3px; }

.size-cell {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: none; border: 1px solid var(--border); border-radius: 4px;
  padding: 4px; cursor: pointer; transition: all 0.1s; width: 42px;
}
.size-cell:hover { border-color: var(--accent); background: var(--bg-hover); }
.size-cell.active { border-color: var(--accent); background: rgba(203, 27, 33, 0.15); }

.cell-preview { display: flex; gap: 1px; }
.preview-col { display: flex; flex-direction: column; gap: 1px; }
.preview-block { width: 5px; height: 5px; border-radius: 1px; background: var(--border); }
.preview-block.filled { background: var(--accent); }
.cell-num { font-size: 8px; color: var(--text-secondary); font-family: monospace; }
.size-cell.active .cell-num { color: var(--accent); }

.menu-enter-active, .menu-leave-active { transition: opacity 0.12s, transform 0.12s; }
.menu-enter-from, .menu-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
