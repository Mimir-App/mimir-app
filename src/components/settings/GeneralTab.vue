<script setup lang="ts">
import { useConfigStore } from '../../stores/config';
import CustomSelect from '../shared/CustomSelect.vue';
import HelpTooltip from '../shared/HelpTooltip.vue';

const configStore = useConfigStore();

const systemTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
const timezoneOptions = [
  'Europe/Madrid', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Rome', 'Europe/Lisbon', 'Europe/Amsterdam', 'Europe/Brussels',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Mexico_City', 'America/Bogota', 'America/Buenos_Aires', 'America/Sao_Paulo',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai',
  'Australia/Sydney', 'Pacific/Auckland', 'UTC',
].map(tz => ({ value: tz, label: tz === systemTz ? `${tz} (sistema)` : tz }))
  .sort((a, b) => a.value === systemTz ? -1 : b.value === systemTz ? 1 : a.label.localeCompare(b.label));
</script>

<template>
  <div class="tab-content">
    <table class="settings-table">
      <tbody>
        <tr>
          <td class="label-cell">Tema <HelpTooltip text="Aspecto visual de la aplicacion. El modo Sistema sigue la preferencia de tu escritorio." /></td>
          <td>
            <CustomSelect v-model="configStore.config.theme" :options="[
              { value: 'dark', label: 'Oscuro', hint: 'Fondo oscuro' },
              { value: 'light', label: 'Claro', hint: 'Fondo blanco' },
              { value: 'system', label: 'Sistema', hint: 'Segun el SO' },
            ]" />
          </td>
          <td class="label-cell"></td>
          <td></td>
        </tr>
        <tr>
          <td class="label-cell">Objetivo semanal <HelpTooltip text="Horas objetivo por dia de la semana. Se usa en el dashboard para las barras de progreso." /></td>
          <td colspan="3">
            <div class="weekly-targets">
              <label v-for="(day, i) in ['Lu', 'Ma', 'Mi', 'Ju', 'Vi']" :key="i" class="day-target">
                <span class="day-label">{{ day }}</span>
                <input type="number" v-model.number="configStore.config.weekly_hour_targets[i]" min="0" max="24" step="0.5" class="day-input" />
              </label>
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">Formato horas <HelpTooltip text="Como se muestran las duraciones en toda la aplicacion: tablas, bloques, timesheets." /></td>
          <td>
            <CustomSelect v-model="configStore.config.hour_format" :options="[
              { value: 'hm', label: 'Horas:Minutos', hint: '1:30' },
              { value: 'decimal', label: 'Decimal', hint: '1.5h' },
              { value: 'minutes', label: 'Minutos', hint: '90m' },
            ]" />
          </td>
          <td class="label-cell">Intervalo refresco <HelpTooltip text="Cada cuantos segundos se actualizan automaticamente las vistas de Issues y MRs." /></td>
          <td>
            <div class="inline-field">
              <input type="number" v-model.number="configStore.config.refresh_interval_seconds" min="30" max="3600" />
              <span class="suffix">seg</span>
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">Formato fecha <HelpTooltip text="Como se muestran las fechas en tablas, agrupaciones y timesheets." /></td>
          <td colspan="3">
            <CustomSelect v-model="configStore.config.date_format" :options="[
              { value: 'eu', label: 'Europeo', hint: '14/03/2026' },
              { value: 'iso', label: 'ISO', hint: '2026-03-14' },
              { value: 'short', label: 'Corto', hint: '14 mar 2026' },
              { value: 'long', label: 'Largo', hint: 'viernes, 14 de marzo de 2026' },
            ]" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">Zona horaria <HelpTooltip text="Zona horaria para mostrar horas de fichaje y bloques. Por defecto usa la del sistema." /></td>
          <td colspan="3">
            <CustomSelect v-model="configStore.config.timezone" :options="timezoneOptions" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">Escala interfaz <HelpTooltip text="Aumenta o reduce el tamano de toda la interfaz: texto, iconos, tablas y botones." /></td>
          <td colspan="3">
            <div class="zoom-control">
              <input type="range" :value="Math.round((configStore.config.font_size / 14) * 100)" @input="configStore.config.font_size = Math.round(($event.target as HTMLInputElement).valueAsNumber * 14 / 100)" min="71" max="157" step="7" class="zoom-slider" />
              <div class="zoom-input-wrap">
                <input type="number" :value="Math.round((configStore.config.font_size / 14) * 100)" @change="configStore.config.font_size = Math.round(($event.target as HTMLInputElement).valueAsNumber * 14 / 100)" min="71" max="157" step="1" class="zoom-input" />
                <span class="zoom-suffix">%</span>
              </div>
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

.settings-table input,
.settings-table select {
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

.weekly-targets {
  display: flex;
  gap: 6px;
}

.day-target {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.day-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.day-input {
  width: 48px;
  text-align: center;
  padding: 4px !important;
  font-size: 13px;
}

.zoom-control {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.zoom-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  outline: none;
  border: none !important;
  padding: 0 !important;
}

.zoom-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
}

.zoom-input-wrap {
  display: flex;
  align-items: center;
  gap: 2px;
}

.zoom-input {
  width: 52px;
  text-align: center;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
}

.zoom-suffix {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
