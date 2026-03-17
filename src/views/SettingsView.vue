<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';
import { api } from '../lib/api';
import CustomSelect from '../components/shared/CustomSelect.vue';
import HelpTooltip from '../components/shared/HelpTooltip.vue';
import IntegrationCard from '../components/shared/IntegrationCard.vue';
import ModalDialog from '../components/shared/ModalDialog.vue';

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const gitlabToken = ref('');
const odooToken = ref('');
const aiToken = ref('');
const saving = ref(false);
const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const integrationStatus = ref<Record<string, unknown>>({});
const daemonPushResult = ref<string | null>(null);
const daemonPushType = ref<'success' | 'error'>('success');
const activeTab = ref('general');

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

const tabs = computed(() => [
  { id: 'general', label: 'General', enabled: true },
  { id: 'capture', label: 'Captura', enabled: true },
  { id: 'odoo', label: 'Odoo', enabled: true },
  { id: 'gitlab', label: 'GitLab', enabled: true },
  { id: 'ai', label: 'IA', enabled: true },
  { id: 'google', label: 'Google', enabled: true },
  { id: 'services', label: 'Servicios', enabled: true },
].filter(t => t.enabled));

interface OdooStatus { configured: boolean; client_type: string | null; }

const gitlabIntegrationConfigured = computed((): boolean => {
  const gitlab = integrationStatus.value?.gitlab;
  return gitlab && typeof gitlab === 'object' ? Boolean((gitlab as Record<string, unknown>).configured) : false;
});

const odooIntegrationStatus = computed((): OdooStatus => {
  const odoo = integrationStatus.value?.odoo;
  if (odoo && typeof odoo === 'object') {
    const s = odoo as Record<string, unknown>;
    return { configured: Boolean(s.configured), client_type: (s.client_type as string) ?? null };
  }
  return { configured: false, client_type: null };
});

// Modals
const showOdooModal = ref(false);
const showGitlabModal = ref(false);
const showGoogleSetupModal = ref(false);

// Google Calendar
const googleCalendarConnected = ref(false);
const authorizingGoogle = ref(false);

async function checkGoogleCalendarStatus() {
  try {
    const result = await api.getGoogleCalendarStatus() as { configured: boolean; connected: boolean };
    googleCalendarConnected.value = result.connected;
  } catch { googleCalendarConnected.value = false; }
}

async function authorizeGoogle() {
  authorizingGoogle.value = true;
  try {
    const result = await api.getGoogleAuthUrl() as { url: string };
    window.open(result.url, '_blank');
    // Poll status every 3s for 2 minutes to detect when user completes auth
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      await checkGoogleCalendarStatus();
      if (googleCalendarConnected.value || attempts > 40) {
        clearInterval(interval);
        authorizingGoogle.value = false;
      }
    }, 3000);
  } catch {
    authorizingGoogle.value = false;
  }
}

async function disconnectGoogle() {
  try {
    await api.disconnectGoogleCalendar();
    googleCalendarConnected.value = false;
  } catch { /* ignore */ }
}

onMounted(async () => {
  await configStore.load();
  await daemonStore.captureHealthCheck();
  if (daemonStore.connected) {
    await refreshIntegrationStatus();
    await checkGoogleCalendarStatus();
  }
});

async function refreshIntegrationStatus() {
  integrationStatus.value = await configStore.getIntegrationStatus();
}

async function saveConfig() {
  saving.value = true;
  message.value = '';
  daemonPushResult.value = null;
  try {
    if (gitlabToken.value) { await configStore.setGitLabToken(gitlabToken.value); gitlabToken.value = ''; }
    if (odooToken.value) { await configStore.setOdooToken(odooToken.value); odooToken.value = ''; }
    if (aiToken.value) { await configStore.setAIToken(aiToken.value); aiToken.value = ''; }
    await configStore.save(configStore.config);
    if (daemonStore.connected) {
      const result = await configStore.pushToDaemon();
      if (result.status === 'ok') {
        daemonPushResult.value = 'Configuracion enviada al daemon';
        daemonPushType.value = 'success';
        await refreshIntegrationStatus();
      } else {
        daemonPushResult.value = result.message ?? 'Error enviando al daemon';
        daemonPushType.value = 'error';
      }
    }
    message.value = 'Configuracion guardada';
    messageType.value = 'success';
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  } finally {
    saving.value = false;
  }
}

async function clearGitLabToken() {
  try { await configStore.deleteGitLabToken(); message.value = 'Token GitLab eliminado'; messageType.value = 'success'; }
  catch (e) { message.value = `Error: ${e}`; messageType.value = 'error'; }
}

async function clearOdooToken() {
  try { await configStore.deleteOdooToken(); message.value = 'Token Odoo eliminado'; messageType.value = 'success'; }
  catch (e) { message.value = `Error: ${e}`; messageType.value = 'error'; }
}

async function clearAIToken() {
  try { await configStore.deleteAIToken(); message.value = 'API key IA eliminada'; messageType.value = 'success'; }
  catch (e) { message.value = `Error: ${e}`; messageType.value = 'error'; }
}

const testingOdoo = ref(false);
const odooTestResult = ref<'ok' | 'fail' | null>(null);
const odooTestMessage = ref('');
const testingGitlab = ref(false);
const gitlabTestResult = ref<'ok' | 'fail' | null>(null);
const gitlabTestMessage = ref('');

async function testOdooConnection() {
  testingOdoo.value = true; odooTestResult.value = null; odooTestMessage.value = '';
  try {
    if (odooToken.value) { await configStore.setOdooToken(odooToken.value); odooToken.value = ''; }
    await configStore.save(configStore.config);
    if (!daemonStore.connected) { odooTestResult.value = 'fail'; odooTestMessage.value = 'Servidor API no conectado'; return; }
    const result = await configStore.pushToDaemon();
    await refreshIntegrationStatus();
    if (result.status === 'ok' && odooIntegrationStatus.value.configured) {
      odooTestResult.value = 'ok'; odooTestMessage.value = 'Conectado a Odoo';
    } else { odooTestResult.value = 'fail'; odooTestMessage.value = result.message ?? 'No se pudo conectar'; }
  } catch (e) { odooTestResult.value = 'fail'; odooTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingOdoo.value = false; }
}

async function testGitlabConnection() {
  testingGitlab.value = true; gitlabTestResult.value = null; gitlabTestMessage.value = '';
  try {
    if (gitlabToken.value) { await configStore.setGitLabToken(gitlabToken.value); gitlabToken.value = ''; }
    await configStore.save(configStore.config);
    if (!daemonStore.connected) { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = 'Servidor API no conectado'; return; }
    const result = await configStore.pushToDaemon();
    await refreshIntegrationStatus();
    if (result.status === 'ok' && gitlabIntegrationConfigured.value) {
      gitlabTestResult.value = 'ok'; gitlabTestMessage.value = 'Conectado a GitLab';
    } else { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = 'No se pudo conectar'; }
  } catch (e) { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingGitlab.value = false; }
}

const togglingCapture = ref(false);
const togglingServer = ref(false);

async function toggleCapture() {
  togglingCapture.value = true;
  try {
    if (daemonStore.captureConnected) {
      await api.stopCapture();
    } else {
      await api.startCapture();
    }
    // Esperar un momento y recheck
    await new Promise(r => setTimeout(r, 1000));
    await daemonStore.captureHealthCheck();
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  } finally {
    togglingCapture.value = false;
  }
}

async function toggleServer() {
  togglingServer.value = true;
  try {
    if (daemonStore.connected) {
      await api.stopServer();
    } else {
      await api.startServer();
    }
    await new Promise(r => setTimeout(r, 1500));
    await daemonStore.healthCheck();
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  } finally {
    togglingServer.value = false;
  }
}
</script>

<template>
  <div class="settings-view">
    <form @submit.prevent="saveConfig" class="settings-form">
      <div class="tabs">
        <button
          v-for="tab in tabs" :key="tab.id" type="button"
          class="tab" :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- General -->
      <div v-show="activeTab === 'general'" class="tab-content">
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

      <!-- Captura -->
      <div v-show="activeTab === 'capture'" class="tab-content">
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

      <!-- Odoo -->
      <div v-show="activeTab === 'odoo'" class="tab-content">
        <IntegrationCard
          name="Odoo"
          icon="O"
          description="Conecta con tu servidor Odoo para imputar horas, gestionar proyectos y fichar jornada."
          :connected="odooIntegrationStatus.configured"
          connect-label="Configurar Odoo"
          disconnect-label="Desconectar"
          @connect="showOdooModal = true"
          @disconnect="clearOdooToken"
        >
          <template #status>
            <p class="session-detail">{{ configStore.config.odoo_username }} — {{ configStore.config.odoo_url }}</p>
          </template>
          <template #details>
            <table class="settings-table">
              <tbody>
                <tr>
                  <td class="label-cell">Servidor</td>
                  <td>{{ configStore.config.odoo_url }}</td>
                  <td class="label-cell">Version</td>
                  <td>{{ configStore.config.odoo_version }}</td>
                </tr>
                <tr>
                  <td class="label-cell">Usuario</td>
                  <td>{{ configStore.config.odoo_username }}</td>
                  <td class="label-cell">Base de datos</td>
                  <td>{{ configStore.config.odoo_db }}</td>
                </tr>
              </tbody>
            </table>
            <div style="margin-top: 12px;">
              <button type="button" class="btn btn-secondary btn-sm" @click="showOdooModal = true">Editar configuracion</button>
            </div>
          </template>
        </IntegrationCard>

        <ModalDialog title="Configurar Odoo" :open="showOdooModal" @close="showOdooModal = false">
          <table class="settings-table">
            <tbody>
              <tr>
                <td class="label-cell">URL</td>
                <td><input type="url" v-model="configStore.config.odoo_url" placeholder="https://odoo.example.com" /></td>
              </tr>
              <tr>
                <td class="label-cell">Version</td>
                <td>
                  <CustomSelect v-model="configStore.config.odoo_version" :options="[
                    { value: 'v11', label: 'Odoo v11', hint: 'XMLRPC' },
                    { value: 'v16', label: 'Odoo v16+', hint: 'REST / OAuth' },
                  ]" />
                </td>
              </tr>
              <tr>
                <td class="label-cell">Base de datos</td>
                <td><input type="text" v-model="configStore.config.odoo_db" placeholder="nombre_base_datos" /></td>
              </tr>
              <tr>
                <td class="label-cell">Usuario</td>
                <td><input type="text" v-model="configStore.config.odoo_username" placeholder="usuario@empresa.com" /></td>
              </tr>
              <tr>
                <td class="label-cell">Token</td>
                <td>
                  <div class="token-field">
                    <input type="password" v-model="odooToken" :placeholder="configStore.config.odoo_token_stored ? '***** (guardado)' : 'Contrasena o API key'" />
                  </div>
                </td>
              </tr>
              <tr>
                <td></td>
                <td>
                  <div class="connection-test">
                    <button type="button" class="btn btn-secondary btn-sm" @click="testOdooConnection" :disabled="testingOdoo">
                      {{ testingOdoo ? 'Probando...' : 'Probar conexion' }}
                    </button>
                    <span v-if="odooTestResult === 'ok'" class="conn-ok">{{ odooTestMessage }}</span>
                    <span v-else-if="odooTestResult === 'fail'" class="conn-fail">{{ odooTestMessage }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </ModalDialog>
      </div>

      <!-- GitLab -->
      <div v-show="activeTab === 'gitlab'" class="tab-content">
        <IntegrationCard
          name="GitLab"
          icon="G"
          description="Conecta con tu instancia GitLab para ver issues y merge requests asignadas."
          :connected="gitlabIntegrationConfigured"
          connect-label="Configurar GitLab"
          disconnect-label="Desconectar"
          @connect="showGitlabModal = true"
          @disconnect="clearGitLabToken"
        >
          <template #status>
            <p class="session-detail">{{ configStore.config.gitlab_url.replace(/^https?:\/\//, '') }}</p>
          </template>
          <template #details>
            <table class="settings-table">
              <tbody>
                <tr>
                  <td class="label-cell">Servidor</td>
                  <td>{{ configStore.config.gitlab_url }}</td>
                  <td class="label-cell">Auth</td>
                  <td>Personal Access Token</td>
                </tr>
              </tbody>
            </table>
            <div style="margin-top: 12px;">
              <button type="button" class="btn btn-secondary btn-sm" @click="showGitlabModal = true">Editar configuracion</button>
            </div>
          </template>
        </IntegrationCard>

        <ModalDialog title="Configurar GitLab" :open="showGitlabModal" @close="showGitlabModal = false">
          <table class="settings-table">
            <tbody>
              <tr>
                <td class="label-cell">URL</td>
                <td><input type="url" v-model="configStore.config.gitlab_url" placeholder="https://gitlab.example.com" /></td>
              </tr>
              <tr>
                <td class="label-cell">Token</td>
                <td>
                  <div class="token-field">
                    <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
                  </div>
                </td>
              </tr>
              <tr>
                <td></td>
                <td>
                  <div class="connection-test">
                    <button type="button" class="btn btn-secondary btn-sm" @click="testGitlabConnection" :disabled="testingGitlab">
                      {{ testingGitlab ? 'Probando...' : 'Probar conexion' }}
                    </button>
                    <span v-if="gitlabTestResult === 'ok'" class="conn-ok">{{ gitlabTestMessage }}</span>
                    <span v-else-if="gitlabTestResult === 'fail'" class="conn-fail">{{ gitlabTestMessage }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </ModalDialog>

        <!-- Scoring: prioridad de labels + notas -->
        <div class="setting-group">
          <h3 class="setting-group-title">Scoring de issues</h3>
          <table class="settings-table">
            <tbody>
              <tr>
                <td class="label-cell">Comentarios en detalle de issue <HelpTooltip text="Numero de comentarios recientes a mostrar al abrir el detalle de una issue." /></td>
                <td>
                  <div class="inline-field">
                    <input type="number" v-model.number="configStore.config.issue_notes_count" min="1" max="20" />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <p class="section-hint" style="margin-top: 16px;">
            Mapeo de prioridad de labels: asigna un peso (0-100) a cada label de GitLab para influir en el scoring de issues.
          </p>
          <table class="settings-table priority-labels-table">
            <thead>
              <tr>
                <th>Label</th>
                <th style="width: 100px;">Peso</th>
                <th style="width: 40px;"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(rule, idx) in configStore.config.gitlab_priority_labels" :key="idx">
                <td><input type="text" v-model="rule.label" placeholder="Ej: priority::1" /></td>
                <td><input type="number" v-model.number="rule.weight" min="0" max="100" /></td>
                <td class="action-cell">
                  <button type="button" class="btn btn-danger btn-sm" @click="configStore.config.gitlab_priority_labels.splice(idx, 1)">
                    &times;
                  </button>
                </td>
              </tr>
              <tr v-if="configStore.config.gitlab_priority_labels.length === 0">
                <td colspan="3" class="empty-hint">Sin reglas de prioridad. Anade una para personalizar el scoring.</td>
              </tr>
            </tbody>
          </table>
          <div style="margin-top: 8px;">
            <button type="button" class="btn btn-secondary btn-sm" @click="configStore.config.gitlab_priority_labels.push({ label: '', weight: 50 })">
              Anadir regla
            </button>
          </div>
        </div>
      </div>

      <!-- IA -->
      <div v-show="activeTab === 'ai'" class="tab-content">
        <table class="settings-table">
          <tbody>
            <tr>
              <td class="label-cell">Proveedor <HelpTooltip text="Servicio de IA para generar descripciones automaticas de los bloques de actividad." /></td>
              <td colspan="3">
                <CustomSelect v-model="configStore.config.ai_provider" :options="[
                  { value: 'none', label: 'Desactivado' },
                  { value: 'gemini', label: 'Google Gemini', hint: 'gemini-2.0-flash' },
                  { value: 'claude', label: 'Anthropic Claude', hint: 'claude-haiku' },
                  { value: 'openai', label: 'OpenAI', hint: 'gpt-4o-mini' },
                ]" />
              </td>
            </tr>
            <template v-if="configStore.config.ai_provider !== 'none'">
              <tr>
                <td class="label-cell">API Key <HelpTooltip text="Clave de API del proveedor seleccionado. Se guarda de forma segura en el keyring." /></td>
                <td colspan="3">
                  <div class="token-field">
                    <input type="password" v-model="aiToken" :placeholder="configStore.config.ai_api_key_stored ? '***** (guardada)' : 'API key'" />
                    <button v-if="configStore.config.ai_api_key_stored" type="button" class="btn btn-danger btn-sm" @click="clearAIToken">Eliminar</button>
                  </div>
                </td>
              </tr>
              <tr>
                <td class="label-cell">Perfil <HelpTooltip text="Tu rol profesional. La IA adapta el lenguaje de las descripciones segun este perfil." /></td>
                <td>
                  <CustomSelect v-model="configStore.config.ai_user_role" :options="[
                    { value: 'technical', label: 'Tecnico', hint: 'Desarrollo, ops' },
                    { value: 'functional', label: 'Funcional', hint: 'Consultor, analista' },
                    { value: 'other', label: 'Otro' },
                  ]" />
                </td>
                <td class="label-cell"></td>
                <td></td>
              </tr>
              <tr>
                <td class="label-cell">Contexto <HelpTooltip text="Informacion adicional sobre tu trabajo. Ayuda a la IA a generar descripciones mas precisas y relevantes." /></td>
                <td colspan="3">
                  <textarea v-model="configStore.config.ai_custom_context" rows="3" placeholder="Ej: Desarrollador backend, modulos account y sale"></textarea>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <p v-if="configStore.config.ai_provider !== 'none'" class="hint">
          Las descripciones se generan automaticamente al cerrar cada bloque de actividad.
        </p>
      </div>

      <!-- Servicios -->
      <!-- Google -->
      <div v-show="activeTab === 'google'" class="tab-content">
        <IntegrationCard
          name="Google"
          icon="G"
          description="Inicia sesion con tu cuenta de Google para acceder a Calendar, Meet y otros servicios."
          :connected="googleCalendarConnected"
          :connect-label="authorizingGoogle ? 'Esperando autorizacion...' : 'Iniciar sesion con Google'"
          disconnect-label="Cerrar sesion"
          @connect="configStore.config.google_client_id ? authorizeGoogle() : (showGoogleSetupModal = true)"
          @disconnect="disconnectGoogle"
        >
          <template #setup>
            <div v-if="!configStore.config.google_client_id">
              <button type="button" class="btn btn-secondary btn-sm" @click="showGoogleSetupModal = true">Configurar credenciales</button>
            </div>
          </template>
          <template #status>
            <p class="session-detail">Cuenta autorizada con acceso a los servicios configurados</p>
          </template>
          <template #details>
            <table class="settings-table">
              <tbody>
                <tr>
                  <td class="label-cell">Autorizaciones</td>
                  <td>Google Calendar (lectura)</td>
                  <td class="label-cell">Servicios</td>
                  <td><span class="service-chip active">Calendar — Deteccion de reuniones</span></td>
                </tr>
              </tbody>
            </table>
            <div style="margin-top: 12px;">
              <button type="button" class="btn btn-secondary btn-sm" @click="showGoogleSetupModal = true">Editar credenciales</button>
            </div>
          </template>
        </IntegrationCard>

        <ModalDialog title="Credenciales Google OAuth2" :open="showGoogleSetupModal" @close="showGoogleSetupModal = false">
          <table class="settings-table">
            <tbody>
              <tr>
                <td class="label-cell">Client ID</td>
                <td><input type="text" v-model="configStore.config.google_client_id" placeholder="123456789.apps.googleusercontent.com" /></td>
              </tr>
              <tr>
                <td class="label-cell">Client Secret</td>
                <td><input type="password" v-model="configStore.config.google_client_secret" placeholder="GOCSPX-..." /></td>
              </tr>
            </tbody>
          </table>
          <div class="google-help">
            <p>Como obtener las credenciales:</p>
            <ol>
              <li>Ve a <a href="https://console.cloud.google.com" target="_blank" rel="noopener">Google Cloud Console</a></li>
              <li>Crea un proyecto o usa uno existente</li>
              <li>Activa la API de Google Calendar</li>
              <li>En Credentials, crea un OAuth 2.0 Client ID (tipo "Web application")</li>
              <li>Anade <code>http://127.0.0.1:9477/oauth/google/callback</code> como Authorized redirect URI</li>
            </ol>
          </div>
        </ModalDialog>
      </div>

      <!-- Servicios -->
      <div v-show="activeTab === 'services'" class="tab-content">
        <table class="status-table">
          <thead>
            <tr>
              <th>Servicio</th>
              <th>Estado</th>
              <th>Puerto</th>
              <th>Detalle</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="service-name">Captura de actividad <HelpTooltip text="Servicio systemd que captura la ventana activa, proyecto git y rama cada 30 segundos. Debe estar siempre activo." /></td>
              <td>
                <span class="badge" :class="daemonStore.captureConnected ? 'ok' : 'off'">
                  {{ daemonStore.captureConnected ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="mono">9476</td>
              <td class="detail">Proceso systemd, siempre activo</td>
              <td class="action-cell">
                <button
                  type="button"
                  class="btn btn-sm"
                  :class="daemonStore.captureConnected ? 'btn-danger' : 'btn-success'"
                  :disabled="togglingCapture"
                  @click="toggleCapture"
                >
                  {{ togglingCapture ? '...' : (daemonStore.captureConnected ? 'Detener' : 'Iniciar') }}
                </button>
              </td>
            </tr>
            <tr>
              <td class="service-name">Servidor API <HelpTooltip text="Servidor que gestiona bloques, integraciones con Odoo/GitLab y descripciones IA. Se lanza automaticamente al abrir la app." /></td>
              <td>
                <span class="badge" :class="daemonStore.connected ? 'ok' : 'off'">
                  {{ daemonStore.connected ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="mono">{{ configStore.config.daemon_port }}</td>
              <td class="detail">
                <template v-if="daemonStore.connected">
                  <span class="mode-badge" :class="daemonStore.status.mode">{{ daemonStore.modeLabel }}</span>
                  {{ daemonStore.status.blocks_today }} bloques hoy — Uptime {{ Math.floor(daemonStore.status.uptime_seconds / 60) }}min
                </template>
                <template v-else>Lanzado al abrir la app</template>
              </td>
              <td class="action-cell">
                <button
                  type="button"
                  class="btn btn-sm"
                  :class="daemonStore.connected ? 'btn-danger' : 'btn-success'"
                  :disabled="togglingServer"
                  @click="toggleServer"
                >
                  {{ togglingServer ? '...' : (daemonStore.connected ? 'Detener' : 'Iniciar') }}
                </button>
              </td>
            </tr>
            <tr>
              <td class="service-name">Odoo <HelpTooltip text="Integracion con Odoo para enviar partes de horas. Configurar en la pestaña Odoo." /></td>
              <td>
                <span class="badge" :class="odooIntegrationStatus.configured ? 'ok' : 'off'">
                  {{ odooIntegrationStatus.configured ? 'Conectado' : 'No' }}
                </span>
              </td>
              <td class="mono">—</td>
              <td class="detail">
                <template v-if="odooIntegrationStatus.configured">
                  {{ configStore.config.odoo_username || '—' }} — {{ odooIntegrationStatus.client_type }}
                </template>
                <template v-else>Configurar en pestaña Odoo</template>
              </td>
              <td></td>
            </tr>
            <tr>
              <td class="service-name">GitLab <HelpTooltip text="Integracion con GitLab para ver issues y merge requests asignadas. Configurar en la pestaña GitLab." /></td>
              <td>
                <span class="badge" :class="gitlabIntegrationConfigured ? 'ok' : 'off'">
                  {{ gitlabIntegrationConfigured ? 'Conectado' : 'No' }}
                </span>
              </td>
              <td class="mono">—</td>
              <td class="detail">
                <template v-if="gitlabIntegrationConfigured">
                  {{ configStore.config.gitlab_url.replace(/^https?:\/\//, '') }} — API v4
                </template>
                <template v-else>Configurar en pestaña GitLab</template>
              </td>
              <td></td>
            </tr>
            <tr>
              <td class="service-name">Inteligencia Artificial <HelpTooltip text="Genera descripciones automaticas de cada bloque de actividad usando IA. Configurar en la pestaña IA." /></td>
              <td>
                <span class="badge" :class="configStore.config.ai_provider !== 'none' ? (configStore.config.ai_api_key_stored ? 'ok' : 'warn') : 'off'">
                  {{ configStore.config.ai_provider !== 'none' ? (configStore.config.ai_api_key_stored ? 'Activo' : 'Sin API key') : 'Desactivado' }}
                </span>
              </td>
              <td class="mono">—</td>
              <td class="detail">
                <template v-if="configStore.config.ai_provider !== 'none'">
                  {{ configStore.config.ai_provider.charAt(0).toUpperCase() + configStore.config.ai_provider.slice(1) }}
                  — Perfil {{ configStore.config.ai_user_role }}
                </template>
                <template v-else>Configurar en pestaña IA</template>
              </td>
              <td></td>
            </tr>
            <tr>
              <td class="service-name">Google Calendar <HelpTooltip text="Conecta con Google Calendar para detectar reuniones automaticamente y enriquecer los bloques con datos del evento." /></td>
              <td>
                <span class="badge" :class="googleCalendarConnected ? 'ok' : 'off'">
                  {{ googleCalendarConnected ? 'Conectado' : 'No' }}
                </span>
              </td>
              <td class="mono">—</td>
              <td class="detail">
                <template v-if="googleCalendarConnected">Eventos del calendario enriquecen las senales</template>
                <template v-else-if="configStore.config.google_client_id">Autoriza el acceso a tu calendario</template>
                <template v-else>Configura Client ID y Secret en la pestaña Google</template>
              </td>
              <td class="action-cell">
                <button
                  v-if="configStore.config.google_client_id && !googleCalendarConnected"
                  type="button"
                  class="btn btn-sm btn-success"
                  :disabled="authorizingGoogle"
                  @click="authorizeGoogle"
                >
                  {{ authorizingGoogle ? 'Abriendo...' : 'Autorizar' }}
                </button>
                <button
                  v-else-if="googleCalendarConnected"
                  type="button"
                  class="btn btn-sm btn-danger"
                  @click="disconnectGoogle"
                >
                  Desconectar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="daemonPushResult" class="push-banner" :class="daemonPushType">
        {{ daemonPushResult }}
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
        <span v-if="message" class="save-msg" :class="messageType">{{ message }}</span>
      </div>
    </form>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  justify-content: center;
}

.settings-form {
  width: 100%;
  max-width: 860px;
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 2px solid var(--border);
  margin-bottom: 20px;
}

.tab {
  flex: 1;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
}

.tab:hover { color: var(--text-primary); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* Tab content */
.tab-content {
  margin-bottom: 20px;
}

/* Settings table (form fields) */
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
.settings-table select,
.settings-table textarea {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.settings-table textarea {
  resize: vertical;
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

.token-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.token-field input {
  flex: 1;
}

.connection-test {
  display: flex;
  align-items: center;
  gap: 8px;
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

.conn-ok { color: var(--success); font-size: 12px; }
.conn-fail { color: var(--error); font-size: 12px; }

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

.hint {
  font-size: 11px;
  color: var(--text-secondary);
  font-style: italic;
  margin-top: 8px;
  padding-left: 130px;
}

/* Status table (services) */
.status-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.status-table th {
  text-align: left;
  padding: 10px 10px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 12px;
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.status-table td {
  padding: 10px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.status-table tr:hover td {
  background: var(--bg-hover);
}

.service-name {
  font-weight: 500;
  white-space: nowrap;
}

.mono {
  font-family: monospace;
  color: var(--text-secondary);
}

.detail {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
}

.badge.ok { background: rgba(78, 201, 176, 0.15); color: var(--success); }
.badge.off { background: rgba(162, 176, 180, 0.15); color: var(--text-secondary); }
.badge.warn { background: rgba(220, 220, 170, 0.15); color: var(--warning); }

.mode-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  margin-right: 4px;
}

.mode-badge.active { background: rgba(78, 201, 176, 0.15); color: var(--success); }
.mode-badge.silent { background: rgba(220, 220, 170, 0.15); color: var(--warning); }
.mode-badge.paused { background: rgba(241, 76, 76, 0.15); color: var(--error); }

/* Banners & actions */
.push-banner {
  padding: 8px 14px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 12px;
}

.push-banner.success { background: rgba(78, 201, 176, 0.1); border: 1px solid var(--success); color: var(--success); }
.push-banner.error { background: rgba(241, 76, 76, 0.1); border: 1px solid var(--error); color: var(--error); }

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn {
  padding: 8px 20px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-hover); }
.btn-success { background: var(--success); color: white; }
.btn-success:hover:not(:disabled) { opacity: 0.85; }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: rgba(241, 76, 76, 0.1); }
.btn:disabled { opacity: 0.5; }

.action-cell { white-space: nowrap; }

.save-msg { font-size: 13px; }
.save-msg.success { color: var(--success); }
.save-msg.error { color: var(--error); }

/* Google */
.google-login { display: flex; justify-content: center; padding: 24px 0; }
.google-login-card { max-width: 480px; text-align: center; }
.google-login-card h3 { margin: 12px 0 8px; }
.google-login-card p { color: var(--text-secondary); font-size: 13px; margin-bottom: 16px; }
.google-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; color: var(--accent); margin: 0 auto; }
.google-icon.connected { background: var(--success); color: white; }
.google-login-btn { margin-top: 16px; padding: 12px 32px; font-size: 15px; }
.google-setup { text-align: left; margin: 16px 0; }
.google-help { margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 6px; font-size: 13px; text-align: left; }
.google-help ol { margin: 8px 0 0 20px; }
.google-help li { margin-bottom: 4px; }
.google-help code { background: var(--bg-card); padding: 2px 4px; border-radius: 3px; font-size: 12px; }
.google-connected { padding: 8px 0; }
.google-session-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
.google-session-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.google-session-header h3 { margin: 0; }
.session-detail { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }
.google-services { display: flex; flex-wrap: wrap; gap: 8px; }
.service-chip { font-size: 12px; padding: 4px 10px; border-radius: 4px; background: var(--bg-card); border: 1px solid var(--border); }
.service-chip.active { border-color: var(--success); color: var(--success); }
.google-actions { margin-top: 16px; display: flex; justify-content: flex-end; }

/* Capture toggles */
.section-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
.toggle { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.toggle input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); }
.toggle-label { font-size: 13px; color: var(--text-secondary); }

/* Setting groups */
.setting-group {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.setting-group-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

/* Priority labels table */
.priority-labels-table {
  border: 1px solid var(--border);
  border-radius: 4px;
}

.priority-labels-table th {
  text-align: left;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}

.priority-labels-table td {
  border-bottom: 1px solid var(--border);
}

.priority-labels-table tr:last-child td {
  border-bottom: none;
}

.empty-hint {
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
  padding: 16px 10px !important;
}
</style>
