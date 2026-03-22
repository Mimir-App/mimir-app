<script setup lang="ts">
import { ref, computed, onMounted, type Component } from 'vue';
import { useConfigStore } from '../stores/config';
import DashboardGrid from '../components/shared/DashboardGrid.vue';
import WidgetGallery from '../components/dashboard/WidgetGallery.vue';
import WidgetConfigModal from '../components/dashboard/WidgetConfigModal.vue';
import {
  createWidget,
  getDefaultWidgets,
  type DashboardWidget,
} from '../lib/widget-registry';
import { Pencil, Plus, RotateCcw, X as XIcon, Save } from 'lucide-vue-next';

// Widget components
import JornadaWidget from '../components/dashboard/widgets/JornadaWidget.vue';
import ServiciosWidget from '../components/dashboard/widgets/ServiciosWidget.vue';
import HorasHoyWidget from '../components/dashboard/widgets/HorasHoyWidget.vue';
import ProgresoWidget from '../components/dashboard/widgets/ProgresoWidget.vue';
import TopIssuesWidget from '../components/dashboard/widgets/TopIssuesWidget.vue';
import MRsPendientesWidget from '../components/dashboard/widgets/MRsPendientesWidget.vue';
import TodosWidget from '../components/dashboard/widgets/TodosWidget.vue';
import HorasSemanaWidget from '../components/dashboard/widgets/HorasSemanaWidget.vue';
import CalendarioWidget from '../components/dashboard/widgets/CalendarioWidget.vue';
import IssuesProyectoWidget from '../components/dashboard/widgets/IssuesProyectoWidget.vue';

const configStore = useConfigStore();

const componentMap: Record<string, Component> = {
  jornada: JornadaWidget,
  servicios: ServiciosWidget,
  horas_hoy: HorasHoyWidget,
  progreso: ProgresoWidget,
  top_issues: TopIssuesWidget,
  mrs_pendientes: MRsPendientesWidget,
  todos: TodosWidget,
  horas_semana: HorasSemanaWidget,
  calendario: CalendarioWidget,
  issues_proyecto: IssuesProyectoWidget,
};

// --- Estado ---

const editing = ref(false);
const galleryOpen = ref(false);
const configModalOpen = ref(false);
const configuringWidget = ref<DashboardWidget | null>(null);

// Widgets en memoria durante la edicion
const editWidgets = ref<DashboardWidget[]>([]);

// Widgets activos: en edicion usamos la copia local, si no la config guardada
const savedWidgets = computed<DashboardWidget[]>(() => {
  const stored = configStore.config.dashboard_widgets;
  return stored && stored.length > 0 ? (stored as DashboardWidget[]) : getDefaultWidgets();
});

const currentWidgets = computed(() =>
  editing.value ? editWidgets.value : savedWidgets.value
);

// --- Edicion ---

function startEditing() {
  editWidgets.value = savedWidgets.value.map(w => ({ ...w, config: { ...w.config } }));
  editing.value = true;
}

async function saveLayout() {
  await configStore.save({ dashboard_widgets: editWidgets.value as any });
  editing.value = false;
}

function cancelEditing() {
  editing.value = false;
}

function resetLayout() {
  editWidgets.value = getDefaultWidgets();
}

// --- Grid events ---

function onWidgetsUpdate(updated: DashboardWidget[]) {
  editWidgets.value = updated;
}

// --- Anadir widget ---

function openGallery() {
  galleryOpen.value = true;
}

function onAddWidget(type: string) {
  const nextPos = editWidgets.value.length > 0
    ? Math.max(...editWidgets.value.map(w => w.position)) + 1
    : 0;
  editWidgets.value = [...editWidgets.value, createWidget(type, nextPos)];
  galleryOpen.value = false;
}

// --- Eliminar widget ---

function onRemoveWidget(widgetId: string) {
  editWidgets.value = editWidgets.value.filter(w => w.id !== widgetId);
}

// --- Configurar widget ---

function onConfigureWidget(widget: DashboardWidget) {
  configuringWidget.value = widget;
  configModalOpen.value = true;
}

function onSaveConfig(config: Record<string, any>) {
  if (!configuringWidget.value) return;
  const id = configuringWidget.value.id;
  editWidgets.value = editWidgets.value.map(w =>
    w.id === id ? { ...w, config } : w
  );
  configModalOpen.value = false;
  configuringWidget.value = null;
}

function onCloseConfigModal() {
  configModalOpen.value = false;
  configuringWidget.value = null;
}

onMounted(() => {
  // Config already loaded by app shell; nothing extra needed
});
</script>

<template>
  <div class="dashboard">
    <!-- Barra de edicion -->
    <div v-if="editing" class="edit-bar">
      <span class="edit-hint">Arrastra widgets para reordenar. Usa los controles de cada widget para configurar o eliminar.</span>
      <div class="edit-actions">
        <button class="btn-edit add" @click="openGallery"><Plus :size="14" :stroke-width="2" /> Añadir</button>
        <button class="btn-edit reset" @click="resetLayout"><RotateCcw :size="14" :stroke-width="2" /> Resetear</button>
        <button class="btn-edit cancel" @click="cancelEditing"><XIcon :size="14" :stroke-width="2" /> Cancelar</button>
        <button class="btn-edit save" @click="saveLayout"><Save :size="14" :stroke-width="2" /> Guardar</button>
      </div>
    </div>
    <div v-else class="edit-toggle">
      <button class="btn-edit-start" @click="startEditing" title="Editar layout del dashboard">
        <Pencil :size="13" :stroke-width="2" /> Editar dashboard
      </button>
    </div>

    <DashboardGrid
      :widgets="currentWidgets"
      :editing="editing"
      :component-map="componentMap"
      @update:widgets="onWidgetsUpdate"
      @configure="onConfigureWidget"
      @remove="onRemoveWidget"
    />

    <!-- Galeria de widgets -->
    <WidgetGallery
      :open="galleryOpen"
      @close="galleryOpen = false"
      @add="onAddWidget"
    />

    <!-- Modal de configuracion -->
    <WidgetConfigModal
      :widget="configuringWidget"
      :open="configModalOpen"
      @close="onCloseConfigModal"
      @save="onSaveConfig"
    />
  </div>
</template>

<style scoped>
.edit-toggle {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-4);
}

.btn-edit-start {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out);
}

.btn-edit-start:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.edit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--accent-soft);
  border: 1px solid var(--accent);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
  gap: var(--space-2);
}

.edit-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.edit-actions {
  display: flex;
  gap: var(--space-2);
}

.btn-edit {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all var(--duration-base) var(--ease-out);
}

.btn-edit.save {
  background: var(--accent);
  color: white;
  box-shadow: 0 2px 8px var(--accent-glow);
}

.btn-edit.save:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
}

.btn-edit.add {
  background: var(--success-soft);
  color: var(--success);
  border: 1px solid transparent;
}

.btn-edit.add:hover {
  border-color: var(--success);
}

.btn-edit.reset {
  background: var(--warning-soft);
  color: var(--warning);
  border: 1px solid transparent;
}

.btn-edit.reset:hover {
  border-color: var(--warning);
}

.btn-edit.cancel {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-edit.cancel:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
</style>
