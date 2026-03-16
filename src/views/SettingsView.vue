<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';
import { api } from '../lib/api';
import CustomSelect from '../components/shared/CustomSelect.vue';
import HelpTooltip from '../components/shared/HelpTooltip.vue';

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
  { id: 'odoo', label: 'Odoo', enabled: true },
  { id: 'gitlab', label: 'GitLab', enabled: true },
  { id: 'ai', label: 'IA', enabled: true },
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

onMounted(async () => {
  await configStore.load();
  await daemonStore.captureHealthCheck();
  if (daemonStore.connected) await refreshIntegrationStatus();
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

      <!-- Odoo -->
      <div v-show="activeTab === 'odoo'" class="tab-content">
        <table class="settings-table">
          <tbody>
            <tr>
              <td class="label-cell">URL <HelpTooltip text="Direccion del servidor Odoo. Ej: https://odoo.miempresa.com" /></td>
              <td colspan="3"><input type="url" v-model="configStore.config.odoo_url" placeholder="https://odoo.example.com" /></td>
            </tr>
            <tr>
              <td class="label-cell">Version <HelpTooltip text="v11 usa XMLRPC con usuario/contrasena. v16+ usa REST con API key o OAuth." /></td>
              <td>
                <CustomSelect v-model="configStore.config.odoo_version" :options="[
                  { value: 'v11', label: 'Odoo v11', hint: 'XMLRPC' },
                  { value: 'v16', label: 'Odoo v16+', hint: 'REST / OAuth' },
                ]" />
              </td>
              <td class="label-cell">Base de datos <HelpTooltip text="Nombre de la base de datos de Odoo. Necesario para la autenticacion." /></td>
              <td><input type="text" v-model="configStore.config.odoo_db" placeholder="nombre_base_datos" /></td>
            </tr>
            <tr>
              <td class="label-cell">Usuario <HelpTooltip text="Email o nombre de usuario para autenticarse en Odoo." /></td>
              <td colspan="3"><input type="text" v-model="configStore.config.odoo_username" placeholder="usuario@empresa.com" /></td>
            </tr>
            <tr>
              <td class="label-cell">Token <HelpTooltip text="Contrasena (v11) o API key (v16). Se guarda de forma segura en el keyring del sistema." /></td>
              <td colspan="3">
                <div class="token-field">
                  <input type="password" v-model="odooToken" :placeholder="configStore.config.odoo_token_stored ? '***** (guardado)' : 'Contrasena o API key'" />
                  <button v-if="configStore.config.odoo_token_stored" type="button" class="btn btn-danger btn-sm" @click="clearOdooToken">Eliminar</button>
                </div>
              </td>
            </tr>
            <tr>
              <td class="label-cell"></td>
              <td colspan="3">
                <div class="connection-test">
                  <button type="button" class="btn btn-secondary btn-sm" @click="testOdooConnection" :disabled="testingOdoo">
                    {{ testingOdoo ? 'Probando...' : 'Probar conexion' }}
                  </button>
                  <span v-if="odooTestResult === 'ok'" class="conn-ok">{{ odooTestMessage }}</span>
                  <span v-else-if="odooTestResult === 'fail'" class="conn-fail">{{ odooTestMessage }}</span>
                  <span v-else-if="odooIntegrationStatus.configured" class="conn-ok">Conectado ({{ odooIntegrationStatus.client_type }})</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- GitLab -->
      <div v-show="activeTab === 'gitlab'" class="tab-content">
        <table class="settings-table">
          <tbody>
            <tr>
              <td class="label-cell">URL <HelpTooltip text="Direccion de tu instancia GitLab. Ej: https://gitlab.miempresa.com" /></td>
              <td colspan="3"><input type="url" v-model="configStore.config.gitlab_url" placeholder="https://gitlab.example.com" /></td>
            </tr>
            <tr>
              <td class="label-cell">Token <HelpTooltip text="Personal Access Token de GitLab con permisos api y read_user. Se guarda en el keyring del sistema." /></td>
              <td colspan="3">
                <div class="token-field">
                  <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
                  <button v-if="configStore.config.gitlab_token_stored" type="button" class="btn btn-danger btn-sm" @click="clearGitLabToken">Eliminar</button>
                </div>
              </td>
            </tr>
            <tr>
              <td class="label-cell"></td>
              <td colspan="3">
                <div class="connection-test">
                  <button type="button" class="btn btn-secondary btn-sm" @click="testGitlabConnection" :disabled="testingGitlab">
                    {{ testingGitlab ? 'Probando...' : 'Probar conexion' }}
                  </button>
                  <span v-if="gitlabTestResult === 'ok'" class="conn-ok">{{ gitlabTestMessage }}</span>
                  <span v-else-if="gitlabTestResult === 'fail'" class="conn-fail">{{ gitlabTestMessage }}</span>
                  <span v-else-if="gitlabIntegrationConfigured" class="conn-ok">Conectado</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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
</style>
