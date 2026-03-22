<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type Component } from 'vue';
import type { DashboardWidget } from '../../lib/widget-registry';
import { X, Settings2 } from 'lucide-vue-next';

const props = defineProps<{
  widgets: DashboardWidget[];
  editing: boolean;
  componentMap: Record<string, Component>;
}>();

const emit = defineEmits<{
  'update:widgets': [widgets: DashboardWidget[]];
  'configure': [widget: DashboardWidget];
  'remove': [widgetId: string];
}>();

const dragId = ref<string | null>(null);
const dragOverId = ref<string | null>(null);
const menuId = ref<string | null>(null);
const gridEl = ref<HTMLElement | null>(null);

const orderedWidgets = computed(() =>
  [...props.widgets].sort((a, b) => a.position - b.position)
);

function getCols(w: DashboardWidget): number {
  return w.span[1];
}

function getRows(w: DashboardWidget): number {
  return w.span[0];
}

function toggleMenu(id: string, e: MouseEvent) {
  e.stopPropagation();
  menuId.value = menuId.value === id ? null : id;
}

function setSize(widget: DashboardWidget, rows: number, cols: number) {
  const updated = props.widgets.map(w =>
    w.id === widget.id ? { ...w, span: [rows, cols] as [number, number] } : w
  );
  emit('update:widgets', updated);
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
  const ordered = orderedWidgets.value;
  const fromIdx = ordered.findIndex(w => w.id === dragId.value);
  const toIdx = ordered.findIndex(w => w.id === targetId);
  if (fromIdx === -1 || toIdx === -1) return;
  // Swap positions
  const updated = props.widgets.map(w => {
    if (w.id === dragId.value) return { ...w, position: ordered[toIdx].position };
    if (w.id === targetId) return { ...w, position: ordered[fromIdx].position };
    return w;
  });
  emit('update:widgets', updated);
  dragId.value = null;
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
        <span class="widget-label">{{ widget.type }}</span>
        <button class="control-btn remove-btn" @click.stop="emit('remove', widget.id)" title="Eliminar widget">
          <X :size="12" :stroke-width="2" />
        </button>
        <button class="control-btn gear-btn" @click.stop="emit('configure', widget)" title="Configurar widget">
          <Settings2 :size="12" :stroke-width="2" />
        </button>
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
                  @click="setSize(widget, r, c)"
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

      <!-- Contenido del widget -->
      <component
        :is="componentMap[widget.type]"
        :config="widget.config"
      />
    </div>
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(120px, auto);
  gap: var(--space-4);
}

.grid-cell {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  position: relative;
  transition: box-shadow var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out),
              opacity var(--duration-fast);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.grid-cell:hover {
  box-shadow: var(--shadow-md);
}

/* Modo edicion */
.editing .grid-cell {
  border-style: dashed;
  cursor: grab;
}

.editing .grid-cell:active {
  cursor: grabbing;
}

.grid-cell.dragging { opacity: 0.4; transform: scale(0.97); }
.grid-cell.drag-over { box-shadow: var(--shadow-glow); border-color: var(--accent); }

/* Controles */
.cell-controls {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
  position: relative;
}

.widget-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex: 1;
}

.control-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 500;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-mono);
  transition: all var(--duration-fast) var(--ease-out);
}

.control-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--accent);
}

.remove-btn:hover {
  border-color: var(--error);
  color: var(--error);
  background: var(--error-soft);
}

/* Size menu */
.size-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--accent);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  box-shadow: var(--shadow-lg);
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
