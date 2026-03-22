<script setup lang="ts">
import { ref, watch } from 'vue';
import ModalDialog from '../shared/ModalDialog.vue';
import type { DashboardWidget } from '../../lib/widget-registry';

const props = defineProps<{
  widget: DashboardWidget | null;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  save: [config: Record<string, any>];
}>();

// Local copy of config to edit
const localConfig = ref<Record<string, any>>({});

watch(() => props.widget, (w) => {
  localConfig.value = w ? { ...w.config } : {};
}, { immediate: true });

function onSave() {
  emit('save', { ...localConfig.value });
}

const configurableTypes = ['top_issues', 'todos', 'progreso', 'horas_hoy', 'mrs_pendientes'];

function isConfigurable(type: string | undefined): boolean {
  return type ? configurableTypes.includes(type) : false;
}
</script>

<template>
  <ModalDialog title="Configurar widget" :open="open" @close="emit('close')">
    <div v-if="widget" class="config-body">

      <!-- top_issues: numero de items -->
      <template v-if="widget.type === 'top_issues'">
        <div class="field">
          <label class="field-label">Numero de issues a mostrar</label>
          <input
            type="number"
            class="field-input"
            v-model.number="localConfig.count"
            min="1"
            max="20"
          />
        </div>
      </template>

      <!-- todos: numero de items -->
      <template v-else-if="widget.type === 'todos'">
        <div class="field">
          <label class="field-label">Numero de todos a mostrar</label>
          <input
            type="number"
            class="field-input"
            v-model.number="localConfig.count"
            min="1"
            max="20"
          />
        </div>
      </template>

      <!-- progreso: checkboxes para barras -->
      <template v-else-if="widget.type === 'progreso'">
        <div class="field">
          <label class="field-label">Barras visibles</label>
          <div class="checkboxes">
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.hoy" /> Hoy
            </label>
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.semana" /> Semana
            </label>
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.mes" /> Mes
            </label>
          </div>
        </div>
      </template>

      <!-- horas_hoy: objetivo en horas -->
      <template v-else-if="widget.type === 'horas_hoy'">
        <div class="field">
          <label class="field-label">Objetivo de horas</label>
          <input
            type="number"
            class="field-input"
            v-model.number="localConfig.target"
            min="1"
            max="24"
            step="0.5"
          />
        </div>
      </template>

      <!-- mrs_pendientes: filtros -->
      <template v-else-if="widget.type === 'mrs_pendientes'">
        <div class="field">
          <label class="field-label">Filtros activos</label>
          <div class="checkboxes">
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.show_mine" /> Solo mis MRs
            </label>
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.show_conflicts" /> Mostrar conflictos
            </label>
            <label class="checkbox-row">
              <input type="checkbox" v-model="localConfig.show_pipeline" /> Mostrar estado pipeline
            </label>
          </div>
        </div>
      </template>

      <!-- Sin configuracion -->
      <template v-else>
        <p class="no-config">Sin configuracion disponible para este widget.</p>
      </template>

      <!-- Boton guardar solo si hay config -->
      <div v-if="isConfigurable(widget.type)" class="config-actions">
        <button class="btn-save" @click="onSave">Guardar</button>
        <button class="btn-cancel" @click="emit('close')">Cancelar</button>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.config-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field-input {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text-primary);
  font-size: 14px;
  padding: 6px 10px;
  width: 100px;
}

.field-input:focus {
  outline: none;
  border-color: var(--accent);
}

.checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-row input[type="checkbox"] {
  accent-color: var(--accent);
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.no-config {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  padding: 12px 0;
}

.config-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 4px;
}

.btn-save {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 5px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-save:hover {
  background: var(--accent-hover);
}

.btn-cancel {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel:hover {
  background: var(--bg-hover);
}
</style>
