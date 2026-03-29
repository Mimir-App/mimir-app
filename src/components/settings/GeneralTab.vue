<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useConfigStore } from '../../stores/config';
import CustomSelect from '../shared/CustomSelect.vue';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';
import { RotateCcw } from 'lucide-vue-next';

const configStore = useConfigStore();
const router = useRouter();
const confirmingReset = ref(false);
let resetTimer: ReturnType<typeof setTimeout> | null = null;

function requestReset() {
  confirmingReset.value = true;
  resetTimer = setTimeout(() => { confirmingReset.value = false; }, 3000);
}

async function confirmReset() {
  confirmingReset.value = false;
  if (resetTimer) { clearTimeout(resetTimer); resetTimer = null; }
  // Resetear configuraciones a valores por defecto
  await configStore.save({
    ...configStore.config,
    odoo_url: '',
    odoo_db: '',
    odoo_username: '',
    odoo_token_stored: false,
    gitlab_url: '',
    gitlab_token_stored: false,
    github_token_stored: false,
    google_client_id: '',
    google_client_secret: '',
    capture_window: true,
    capture_git: true,
    capture_idle: true,
    capture_audio: true,
    capture_ssh: true,
    section_dashboard: false,
    section_issues: false,
    section_merge_requests: false,
    section_discover: false,
    section_timesheets: false,
    onboarding_completed: false,
  });
  router.push('/onboarding');
}

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
    <SettingGroup title="Apariencia">
      <SettingRow label="Tema" help="Aspecto visual de la aplicacion. El modo Sistema sigue la preferencia de tu escritorio.">
        <CustomSelect v-model="configStore.config.theme" :options="[
          { value: 'dark', label: 'Oscuro', hint: 'Fondo oscuro' },
          { value: 'light', label: 'Claro', hint: 'Fondo blanco' },
          { value: 'system', label: 'Sistema', hint: 'Segun el SO' },
        ]" />
      </SettingRow>
      <SettingRow label="Escala interfaz" help="Aumenta o reduce el tamano de toda la interfaz: texto, iconos, tablas y botones." :fullWidth="true">
        <div class="zoom-control">
          <input type="range" :value="Math.round((configStore.config.font_size / 14) * 100)" @input="configStore.config.font_size = Math.round(($event.target as HTMLInputElement).valueAsNumber * 14 / 100)" min="71" max="157" step="7" class="zoom-slider" />
          <div class="zoom-input-wrap">
            <input type="number" :value="Math.round((configStore.config.font_size / 14) * 100)" @change="configStore.config.font_size = Math.round(($event.target as HTMLInputElement).valueAsNumber * 14 / 100)" min="71" max="157" step="1" class="zoom-input" />
            <span class="zoom-suffix">%</span>
          </div>
        </div>
      </SettingRow>
    </SettingGroup>

    <SettingGroup title="Formato">
      <SettingRow label="Formato horas" help="Como se muestran las duraciones en toda la aplicacion: tablas, bloques, timesheets.">
        <CustomSelect v-model="configStore.config.hour_format" :options="[
          { value: 'hm', label: 'Horas:Minutos', hint: '1:30' },
          { value: 'decimal', label: 'Decimal', hint: '1.5h' },
          { value: 'minutes', label: 'Minutos', hint: '90m' },
        ]" />
      </SettingRow>
      <SettingRow label="Formato fecha" help="Como se muestran las fechas en tablas, agrupaciones y timesheets.">
        <CustomSelect v-model="configStore.config.date_format" :options="[
          { value: 'eu', label: 'Europeo', hint: '14/03/2026' },
          { value: 'iso', label: 'ISO', hint: '2026-03-14' },
          { value: 'short', label: 'Corto', hint: '14 mar 2026' },
          { value: 'long', label: 'Largo', hint: 'viernes, 14 de marzo de 2026' },
        ]" />
      </SettingRow>
      <SettingRow label="Zona horaria" help="Zona horaria para mostrar horas de fichaje y bloques. Por defecto usa la del sistema.">
        <CustomSelect v-model="configStore.config.timezone" :options="timezoneOptions" />
      </SettingRow>
    </SettingGroup>

    <SettingGroup title="Secciones" description="Elige qué secciones se muestran en el menú lateral. Revisar Día y Ajustes están siempre visibles.">
      <SettingRow label="Dashboard" help="Panel con widgets de resumen: jornada, horas, progreso, servicios, etc.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.section_dashboard" />
          <span class="toggle-label">{{ configStore.config.section_dashboard ? 'Visible' : 'Oculto' }}</span>
        </label>
      </SettingRow>
      <SettingRow label="Tareas" help="Vista de issues de GitLab y GitHub con scoring y priorización.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.section_issues" />
          <span class="toggle-label">{{ configStore.config.section_issues ? 'Visible' : 'Oculto' }}</span>
        </label>
      </SettingRow>
      <SettingRow label="Ramas" help="Vista de merge requests y pull requests con estado de pipeline y aprobaciones.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.section_merge_requests" />
          <span class="toggle-label">{{ configStore.config.section_merge_requests ? 'Visible' : 'Oculto' }}</span>
        </label>
      </SettingRow>
      <SettingRow label="Descubrir" help="Búsqueda universal de issues y MRs en todos los repositorios configurados.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.section_discover" />
          <span class="toggle-label">{{ configStore.config.section_discover ? 'Visible' : 'Oculto' }}</span>
        </label>
      </SettingRow>
      <SettingRow label="Parte de horas" help="Vista de timesheets enviados a Odoo con resumen semanal.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.section_timesheets" />
          <span class="toggle-label">{{ configStore.config.section_timesheets ? 'Visible' : 'Oculto' }}</span>
        </label>
      </SettingRow>
    </SettingGroup>

    <SettingGroup title="Actividad">
      <SettingRow label="Objetivo semanal" help="Horas objetivo por dia de la semana. Se usa en el dashboard para las barras de progreso." :fullWidth="true">
        <div class="weekly-targets">
          <label v-for="(day, i) in ['Lu', 'Ma', 'Mi', 'Ju', 'Vi']" :key="i" class="day-target">
            <span class="day-label">{{ day }}</span>
            <input type="number" v-model.number="configStore.config.weekly_hour_targets[i]" min="0" max="24" step="0.5" class="day-input" />
          </label>
        </div>
      </SettingRow>
      <SettingRow label="Intervalo refresco" help="Cada cuantos segundos se actualizan automaticamente las vistas de Issues y MRs.">
        <div class="inline-field">
          <input type="number" v-model.number="configStore.config.refresh_interval_seconds" min="30" max="3600" />
          <span class="suffix">seg</span>
        </div>
      </SettingRow>
    </SettingGroup>

    <SettingGroup title="Configuracion inicial">
      <div class="reset-section">
        <p class="reset-hint">Vuelve a ejecutar el asistente de configuracion inicial. Se borraran las credenciales y secciones activas.</p>
        <button v-if="!confirmingReset" type="button" class="btn-reset" @click="requestReset">
          <RotateCcw :size="14" :stroke-width="2" />
          Repetir configuracion inicial
        </button>
        <button v-else type="button" class="btn-reset btn-reset-confirm" @click="confirmReset">
          Se borraran los datos de integraciones. Confirmar
        </button>
      </div>
    </SettingGroup>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
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

.reset-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reset-hint {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.btn-reset {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  align-self: flex-start;
}

.btn-reset:hover {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.btn-reset-confirm {
  border-color: var(--error);
  color: var(--error);
  background: var(--error-soft);
}

.btn-reset-confirm:hover {
  background: var(--error);
  color: white;
}
</style>
