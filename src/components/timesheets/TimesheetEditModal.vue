<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import ModalDialog from '../shared/ModalDialog.vue';
import CustomSelect from '../shared/CustomSelect.vue';
import { useOdooProjects } from '../../composables/useOdooProjects';
import { useConfigStore } from '../../stores/config';
import { formatDate } from '../../composables/useFormatting';
import { api } from '../../lib/api';
import type { TimesheetEntry } from '../../lib/types';

const props = defineProps<{
  entry: TimesheetEntry | null;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  saved: [];
}>();

const configStore = useConfigStore();
const { projects, tasks, selectedProjectId, loadProjects } = useOdooProjects();

const formProjectId = ref<number | null>(null);
const formTaskId = ref<number | null>(null);
const formDescription = ref('');
const formHours = ref(0);
const saving = ref(false);
const saveError = ref<string | null>(null);

const projectOptions = computed(() =>
  projects.value.map(p => ({ value: p.id, label: p.name }))
);

const taskOptions = computed(() => [
  { value: null as number | null, label: '-- Sin tarea --' },
  ...tasks.value.map(t => ({ value: t.id as number | null, label: t.name })),
]);

const odooEntryUrl = computed(() => {
  if (!props.entry) return '';
  const base = configStore.config.odoo_url.replace(/\/+$/, '');
  return `${base}/web#id=${props.entry.id}&model=account.analytic.line&view_type=form`;
});

// Populate form when entry changes
watch(() => props.entry, (e) => {
  if (e) {
    formProjectId.value = e.project_id;
    formTaskId.value = e.task_id;
    formDescription.value = e.description;
    formHours.value = e.hours;
    saveError.value = null;
    // Load projects if not loaded yet
    if (projects.value.length === 0) {
      loadProjects();
    }
    // Sync selectedProjectId to trigger task loading
    selectedProjectId.value = e.project_id;
  }
}, { immediate: true });

// When project changes, reload tasks via composable and reset task selection
watch(formProjectId, (newId) => {
  selectedProjectId.value = newId;
  // Only reset task if project actually changed from the entry's original
  if (props.entry && newId !== props.entry.project_id) {
    formTaskId.value = null;
  }
});

async function save() {
  if (!props.entry) return;
  saving.value = true;
  saveError.value = null;
  try {
    await api.updateTimesheetEntry(props.entry.id, {
      project_id: formProjectId.value ?? undefined,
      task_id: formTaskId.value ?? undefined,
      description: formDescription.value,
      hours: formHours.value,
    });
    emit('saved');
    emit('close');
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}

function openInOdoo() {
  if (odooEntryUrl.value) {
    window.open(odooEntryUrl.value, '_blank');
  }
}
</script>

<template>
  <ModalDialog title="Editar entrada" :open="open" @close="emit('close')">
    <div v-if="entry" class="edit-form">
      <div class="form-field">
        <label>Fecha</label>
        <span class="readonly-value">{{ formatDate(entry.date) }}</span>
      </div>

      <div class="form-field">
        <label>Proyecto</label>
        <CustomSelect
          v-model="formProjectId"
          :options="projectOptions"
          placeholder="-- Seleccionar proyecto --"
          searchable
        />
      </div>

      <div class="form-field">
        <label>Tarea</label>
        <CustomSelect
          v-model="formTaskId"
          :options="taskOptions"
          placeholder="-- Sin tarea --"
          searchable
        />
      </div>

      <div class="form-field">
        <label>Descripcion</label>
        <textarea
          v-model="formDescription"
          rows="3"
          class="form-textarea"
        />
      </div>

      <div class="form-field">
        <label>Horas</label>
        <input
          v-model.number="formHours"
          type="number"
          step="0.25"
          min="0"
          class="form-input"
        />
      </div>

      <div v-if="saveError" class="save-error">{{ saveError }}</div>

      <div class="form-footer">
        <button class="btn-secondary" @click="openInOdoo">Ir a Odoo</button>
        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.readonly-value {
  font-size: 14px;
  color: var(--text-primary);
  padding: 6px 0;
}

.form-textarea {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.form-input {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
  width: 120px;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent);
}

.save-error {
  color: var(--error, #f14c4c);
  font-size: 12px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 8px 18px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 18px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s;
}

.btn-secondary:hover {
  border-color: var(--accent);
}
</style>
