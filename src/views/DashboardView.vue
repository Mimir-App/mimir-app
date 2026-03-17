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
      <span class="edit-hint">Modo edicion: arrastra widgets, usa &times; para eliminar y ⚙ para configurar</span>
      <div class="edit-actions">
        <button class="btn-edit add" @click="openGallery">+ Anadir widget</button>
        <button class="btn-edit reset" @click="resetLayout">Resetear</button>
        <button class="btn-edit cancel" @click="cancelEditing">Cancelar</button>
        <button class="btn-edit save" @click="saveLayout">Guardar</button>
      </div>
    </div>
    <div v-else class="edit-toggle">
      <button class="btn-edit-start" @click="startEditing" title="Editar layout del dashboard">
        &#x270E; Editar dashboard
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
/* Edit bar */
.edit-toggle {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.btn-edit-start {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-edit-start:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.edit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(203, 27, 33, 0.08);
  border: 1px solid var(--accent);
  border-radius: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.edit-hint {
  font-size: 12px;
  color: var(--text-secondary);
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.btn-edit {
  padding: 5px 14px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn-edit.save {
  background: var(--accent);
  color: white;
}

.btn-edit.save:hover {
  background: var(--accent-hover);
}

.btn-edit.add {
  background: none;
  color: var(--success);
  border: 1px solid var(--success);
}

.btn-edit.add:hover {
  background: rgba(78, 201, 176, 0.1);
}

.btn-edit.reset {
  background: none;
  color: var(--warning);
  border: 1px solid var(--warning);
}

.btn-edit.reset:hover {
  background: rgba(220, 220, 170, 0.1);
}

.btn-edit.cancel {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-edit.cancel:hover {
  background: var(--bg-hover);
}
</style>
