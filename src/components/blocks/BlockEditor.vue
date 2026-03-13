<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { ActivityBlock, OdooProject, OdooTask } from '../../lib/types';
import { useBlocksStore } from '../../stores/blocks';

const props = defineProps<{ block: ActivityBlock }>();
const emit = defineEmits<{ close: [] }>();

const blocksStore = useBlocksStore();
const description = ref(props.block.user_description ?? props.block.ai_description ?? '');
const selectedProject = ref<number | null>(props.block.odoo_project_id);
const selectedTask = ref<number | null>(props.block.odoo_task_id);
const projects = ref<OdooProject[]>([]);
const tasks = ref<OdooTask[]>([]);

onMounted(async () => {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    projects.value = await invoke<OdooProject[]>('get_odoo_projects');
    if (selectedProject.value) {
      tasks.value = await invoke<OdooTask[]>('get_odoo_tasks', {
        projectId: selectedProject.value,
      });
    }
  } catch {
    // Silently handle — projects will be empty
  }
});

async function onProjectChange() {
  selectedTask.value = null;
  tasks.value = [];
  if (selectedProject.value) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      tasks.value = await invoke<OdooTask[]>('get_odoo_tasks', {
        projectId: selectedProject.value,
      });
    } catch {
      // Silently handle
    }
  }
}

async function save() {
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
}
</script>

<template>
  <div class="block-editor">
    <label class="field">
      <span>Descripción</span>
      <textarea v-model="description" rows="2"></textarea>
    </label>
    <label class="field">
      <span>Proyecto Odoo</span>
      <select v-model="selectedProject" @change="onProjectChange">
        <option :value="null">— Seleccionar —</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
    </label>
    <label class="field">
      <span>Tarea</span>
      <select v-model="selectedTask" :disabled="!selectedProject">
        <option :value="null">— Seleccionar —</option>
        <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
      </select>
    </label>
    <div class="editor-actions">
      <button class="btn btn-primary" @click="save">Guardar</button>
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

.field {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.field span {
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

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border);
}
</style>
