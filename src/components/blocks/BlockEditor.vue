<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import type { ActivityBlock, OdooProject, OdooTask } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';
import { api } from '../../lib/api';

const props = defineProps<{ block: ActivityBlock }>();
const emit = defineEmits<{ close: [] }>();

const blocksStore = useBlocksStore();
const description = ref(props.block.user_description ?? props.block.ai_description ?? '');
const selectedProject = ref<number | null>(props.block.odoo_project_id);
const selectedTask = ref<number | null>(props.block.odoo_task_id);
const projects = ref<OdooProject[]>([]);
const tasks = ref<OdooTask[]>([]);
const loadingProjects = ref(false);
const loadingTasks = ref(false);
const saving = ref(false);
const generating = ref(false);
const saveError = ref<string | null>(null);
const projectFilter = ref('');

const filteredProjects = computed(() => {
  if (!projectFilter.value) return projects.value;
  const q = projectFilter.value.toLowerCase();
  return projects.value.filter(p => p.name.toLowerCase().includes(q));
});

onMounted(async () => {
  loadingProjects.value = true;
  try {
    projects.value = await api.getOdooProjects() as OdooProject[];
  } catch {
    // Silently handle -- projects will be empty
  } finally {
    loadingProjects.value = false;
  }

  if (selectedProject.value) {
    await loadTasks(selectedProject.value);
  }
});

async function loadTasks(projectId: number) {
  loadingTasks.value = true;
  tasks.value = [];
  try {
    tasks.value = await api.getOdooTasks(projectId) as OdooTask[];
  } catch {
    // Silently handle
  } finally {
    loadingTasks.value = false;
  }
}

async function onProjectChange() {
  selectedTask.value = null;
  tasks.value = [];
  if (selectedProject.value) {
    await loadTasks(selectedProject.value);
  }
}

async function regenerateDescription() {
  generating.value = true;
  try {
    const result = await api.generateDescription(props.block.id) as { description: string; confidence: number };
    description.value = result.description;
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e);
  } finally {
    generating.value = false;
  }
}

async function save() {
  saving.value = true;
  saveError.value = null;
  try {
    const projectName = projects.value.find(p => p.id === selectedProject.value)?.name ?? null;
    const taskName = tasks.value.find(t => t.id === selectedTask.value)?.name ?? null;

    await blocksStore.updateBlock(props.block.id, {
      user_description: description.value || null,
      odoo_project_id: selectedProject.value,
      odoo_task_id: selectedTask.value,
      odoo_project_name: projectName,
      odoo_task_name: taskName,
    });
    emit('close');
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}

async function saveAndConfirm() {
  saving.value = true;
  saveError.value = null;
  try {
    const projectName = projects.value.find(p => p.id === selectedProject.value)?.name ?? null;
    const taskName = tasks.value.find(t => t.id === selectedTask.value)?.name ?? null;

    await blocksStore.updateBlock(props.block.id, {
      user_description: description.value || null,
      odoo_project_id: selectedProject.value,
      odoo_task_id: selectedTask.value,
      odoo_project_name: projectName,
      odoo_task_name: taskName,
    });
    await blocksStore.confirmBlock(props.block.id);
    emit('close');
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="block-editor">
    <div class="editor-fields">
      <label class="field">
        <span class="field-label">Descripcion</span>
        <div class="desc-field-wrapper">
          <textarea v-model="description" rows="2" placeholder="Describe la actividad..."></textarea>
          <button
            type="button"
            class="btn-regenerate"
            @click="regenerateDescription"
            :disabled="generating"
            title="Generar descripcion con IA"
          >
            {{ generating ? 'Generando...' : 'Generar con IA' }}
          </button>
        </div>
      </label>
      <label class="field">
        <span class="field-label">Proyecto Odoo</span>
        <div class="project-select-wrapper">
          <input
            v-if="projects.length > 10"
            type="text"
            v-model="projectFilter"
            class="project-search"
            placeholder="Filtrar proyectos..."
          />
          <select v-model="selectedProject" @change="onProjectChange" :disabled="loadingProjects">
            <option :value="null">{{ loadingProjects ? 'Cargando...' : '-- Seleccionar proyecto --' }}</option>
            <option v-for="p in filteredProjects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
      </label>
      <label class="field">
        <span class="field-label">Tarea</span>
        <select v-model="selectedTask" :disabled="!selectedProject || loadingTasks">
          <option :value="null">{{ loadingTasks ? 'Cargando...' : '-- Seleccionar tarea --' }}</option>
          <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
      </label>
    </div>

    <div class="editor-context">
      <span v-if="block.project_path" class="context-item" title="Ruta del proyecto">
        {{ block.project_path }}
      </span>
      <span v-if="block.git_branch" class="context-item" title="Rama git">
        {{ block.git_branch }}
      </span>
      <span v-if="block.window_title" class="context-item" :title="block.window_title">
        {{ block.window_title.length > 60 ? block.window_title.slice(0, 60) + '...' : block.window_title }}
      </span>
    </div>

    <div v-if="saveError" class="editor-error">{{ saveError }}</div>

    <div class="editor-actions">
      <button class="btn btn-primary" @click="save" :disabled="saving">
        {{ saving ? 'Guardando...' : 'Guardar' }}
      </button>
      <button
        v-if="block.status === 'auto' && selectedProject"
        class="btn btn-success"
        @click="saveAndConfirm"
        :disabled="saving"
      >
        Guardar y confirmar
      </button>
      <button class="btn btn-secondary" @click="emit('close')">Cancelar</button>
    </div>
  </div>
</template>

<style scoped>
.block-editor {
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--accent);
  border-radius: 6px;
  margin: 4px 0;
}

.editor-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}

.field-label {
  min-width: 100px;
  color: var(--text-secondary);
  padding-top: 4px;
}

.field textarea,
.field select {
  flex: 1;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
}

.field select:disabled {
  opacity: 0.5;
}

.project-select-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.project-search {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.editor-context {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
  padding-left: 108px;
}

.context-item {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-card);
  border-radius: 3px;
  color: var(--text-secondary);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-error {
  color: var(--error);
  font-size: 12px;
  margin-bottom: 8px;
  padding-left: 108px;
}

.editor-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid transparent;
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

.btn-success {
  background: var(--success);
  color: white;
}

.btn-success:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.desc-field-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.btn-regenerate {
  align-self: flex-start;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
}

.btn-regenerate:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.btn-regenerate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
