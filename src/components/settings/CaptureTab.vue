<script setup lang="ts">
import { useConfigStore } from '../../stores/config';
import HelpTooltip from '../shared/HelpTooltip.vue';

const configStore = useConfigStore();
</script>

<template>
  <div class="tab-content">
    <p class="section-hint">Controla que datos recopila el servicio de captura. Los cambios se aplican en el siguiente ciclo de polling.</p>
    <table class="settings-table">
      <tbody>
        <tr>
          <td class="label-cell">Ventana activa <HelpTooltip text="Captura la aplicacion y el titulo de la ventana activa cada 30 segundos. Es el dato principal para construir bloques." /></td>
          <td><label class="toggle"><input type="checkbox" v-model="configStore.config.capture_window" /><span class="toggle-label">{{ configStore.config.capture_window ? 'Activo' : 'Desactivado' }}</span></label></td>
          <td class="label-cell">Proyecto git <HelpTooltip text="Detecta el repositorio git, rama y ultimo commit del proceso activo. Permite agrupar bloques por proyecto." /></td>
          <td><label class="toggle"><input type="checkbox" v-model="configStore.config.capture_git" /><span class="toggle-label">{{ configStore.config.capture_git ? 'Activo' : 'Desactivado' }}</span></label></td>
        </tr>
        <tr>
          <td class="label-cell">Tiempo inactivo <HelpTooltip text="Detecta cuanto tiempo llevas sin tocar teclado o raton. Permite descontar tiempo AFK de los bloques." /></td>
          <td><label class="toggle"><input type="checkbox" v-model="configStore.config.capture_idle" /><span class="toggle-label">{{ configStore.config.capture_idle ? 'Activo' : 'Desactivado' }}</span></label></td>
          <td class="label-cell">Audio / reuniones <HelpTooltip text="Detecta streams de audio activos para identificar videollamadas (Meet, Zoom, Teams, etc.) automaticamente." /></td>
          <td><label class="toggle"><input type="checkbox" v-model="configStore.config.capture_audio" /><span class="toggle-label">{{ configStore.config.capture_audio ? 'Activo' : 'Desactivado' }}</span></label></td>
        </tr>
        <tr>
          <td class="label-cell">Sesiones SSH <HelpTooltip text="Detecta conexiones SSH activas para identificar trabajo en servidores remotos." /></td>
          <td><label class="toggle"><input type="checkbox" v-model="configStore.config.capture_ssh" /><span class="toggle-label">{{ configStore.config.capture_ssh ? 'Activo' : 'Desactivado' }}</span></label></td>
          <td class="label-cell">Umbral inactividad <HelpTooltip text="Minutos sin actividad para cerrar un bloque automaticamente." /></td>
          <td>
            <div class="inline-field">
              <input type="number" v-model.number="configStore.config.refresh_interval_seconds" min="1" max="30" />
              <span class="suffix">min</span>
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">Retencion senales <HelpTooltip text="Dias que se conservan las senales crudas. Pasado este tiempo se eliminan automaticamente para liberar espacio." /></td>
          <td>
            <div class="inline-field">
              <input type="number" v-model.number="configStore.config.signals_retention_days" min="30" max="730" />
              <span class="suffix">dias</span>
            </div>
          </td>
          <td class="label-cell">Retencion bloques <HelpTooltip text="Dias que se conservan los bloques de actividad. Los bloques sincronizados con Odoo se pueden eliminar antes." /></td>
          <td>
            <div class="inline-field">
              <input type="number" v-model.number="configStore.config.blocks_retention_days" min="30" max="1825" />
              <span class="suffix">dias</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}

.section-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }

.settings-table {
  width: 100%;
  border-collapse: collapse;
}

.settings-table td {
  padding: 8px 10px;
  vertical-align: middle;
  font-size: 13px;
}

.label-cell {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  width: 120px;
  text-align: right;
  padding-right: 14px !important;
}

.settings-table input[type="number"] {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.inline-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inline-field input {
  flex: 1;
}

.suffix {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.toggle { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.toggle input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); }
.toggle-label { font-size: 13px; color: var(--text-secondary); }
</style>
