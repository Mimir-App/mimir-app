<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const gitlabToken = ref('');
const odooToken = ref('');
const aiToken = ref('');
const saving = ref(false);
const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const connectionResult = ref<'ok' | 'fail' | null>(null);
const integrationStatus = ref<Record<string, unknown>>({});
const daemonPushResult = ref<string | null>(null);
const daemonPushType = ref<'success' | 'error'>('success');

const hasOdooConfig = computed(() =>
  configStore.config.odoo_url && configStore.config.odoo_token_stored
);

const hasGitLabConfig = computed(() =>
  configStore.config.gitlab_url && configStore.config.gitlab_token_stored
);

interface OdooStatus {
  configured: boolean;
  client_type: string | null;
}

const gitlabIntegrationConfigured = computed((): boolean => {
  const gitlab = integrationStatus.value?.gitlab;
  if (gitlab && typeof gitlab === 'object') {
    return Boolean((gitlab as Record<string, unknown>).configured);
  }
  return false;
});

const odooIntegrationStatus = computed((): OdooStatus => {
  const odoo = integrationStatus.value?.odoo;
  if (odoo && typeof odoo === 'object') {
    const s = odoo as Record<string, unknown>;
    return {
      configured: Boolean(s.configured),
      client_type: (s.client_type as string) ?? null,
    };
  }
  return { configured: false, client_type: null };
});

onMounted(async () => {
  await configStore.load();
  if (daemonStore.connected) {
    await refreshIntegrationStatus();
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
    // Guardar tokens si hay nuevos
    if (gitlabToken.value) {
      await configStore.setGitLabToken(gitlabToken.value);
      gitlabToken.value = '';
    }
    if (odooToken.value) {
      await configStore.setOdooToken(odooToken.value);
      odooToken.value = '';
    }
    if (aiToken.value) {
      await configStore.setAIToken(aiToken.value);
      aiToken.value = '';
    }

    // Guardar configuracion local
    await configStore.save(configStore.config);

    // Enviar configuracion al daemon si esta conectado
    if (daemonStore.connected) {
      const result = await configStore.pushToDaemon();
      if (result.status === 'ok') {
        daemonPushResult.value = 'Configuracion enviada al daemon';
        daemonPushType.value = 'success';
        await refreshIntegrationStatus();
      } else if (result.status === 'partial') {
        daemonPushResult.value = result.message ?? 'Configuracion parcialmente aplicada';
        daemonPushType.value = 'error';
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

async function testConnection() {
  connectionResult.value = null;
  const ok = await daemonStore.healthCheck();
  connectionResult.value = ok ? 'ok' : 'fail';
  if (ok) {
    await refreshIntegrationStatus();
  }
}

async function clearGitLabToken() {
  try {
    await configStore.deleteGitLabToken();
    message.value = 'Token GitLab eliminado';
    messageType.value = 'success';
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  }
}

async function clearOdooToken() {
  try {
    await configStore.deleteOdooToken();
    message.value = 'Token Odoo eliminado';
    messageType.value = 'success';
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  }
}

async function clearAIToken() {
  try {
    await configStore.deleteAIToken();
    message.value = 'API key IA eliminada';
    messageType.value = 'success';
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  }
}
</script>

<template>
  <div class="settings-view">
    <form @submit.prevent="saveConfig" class="settings-form">
      <!-- Daemon -->
      <fieldset class="settings-group">
        <legend>Daemon</legend>
        <label class="field">
          <span>Puerto</span>
          <input type="number" v-model.number="configStore.config.daemon_port" min="1024" max="65535" />
        </label>
        <div class="field">
          <span>Conexion</span>
          <div class="connection-test">
            <button type="button" class="btn btn-secondary btn-sm" @click="testConnection" :disabled="daemonStore.checking">
              {{ daemonStore.checking ? 'Probando...' : 'Probar conexion' }}
            </button>
            <span v-if="connectionResult === 'ok'" class="conn-ok">Conectado -- {{ daemonStore.statusText }}</span>
            <span v-else-if="connectionResult === 'fail'" class="conn-fail">No se pudo conectar al daemon en puerto {{ configStore.config.daemon_port }}</span>
            <span v-else-if="daemonStore.connected" class="conn-ok">{{ daemonStore.statusText }}</span>
            <span v-else class="conn-fail">Desconectado</span>
          </div>
        </div>
        <div class="field" v-if="daemonStore.connected">
          <span>Estado</span>
          <div class="daemon-info">
            <span class="mode-badge" :class="daemonStore.status.mode">{{ daemonStore.modeLabel }}</span>
            <span class="info-text">{{ daemonStore.status.blocks_today }} bloques hoy</span>
            <span class="info-text">Uptime: {{ Math.floor(daemonStore.status.uptime_seconds / 60) }}min</span>
          </div>
        </div>
        <div class="field" v-if="daemonStore.connected">
          <span>Integraciones</span>
          <div class="daemon-info">
            <span class="integration-badge"
              :class="odooIntegrationStatus.configured ? 'configured' : 'not-configured'">
              Odoo: {{ odooIntegrationStatus.configured ? 'Conectado' : 'No configurado' }}
            </span>
            <span class="integration-badge"
              :class="gitlabIntegrationConfigured ? 'configured' : 'not-configured'">
              GitLab: {{ gitlabIntegrationConfigured ? 'Conectado' : 'No configurado' }}
            </span>
          </div>
        </div>
      </fieldset>

      <!-- GitLab -->
      <fieldset class="settings-group">
        <legend>GitLab</legend>
        <label class="field">
          <span>URL</span>
          <input type="url" v-model="configStore.config.gitlab_url" placeholder="https://gitlab.example.com" />
        </label>
        <div class="field">
          <span>Token</span>
          <div class="token-field">
            <input type="password" v-model="gitlabToken"
              :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado en keyring)' : 'Personal Access Token'" />
            <button
              v-if="configStore.config.gitlab_token_stored"
              type="button"
              class="btn btn-danger btn-sm"
              @click="clearGitLabToken"
              title="Eliminar token"
            >
              Eliminar
            </button>
          </div>
        </div>
        <div class="field-hint" v-if="hasGitLabConfig">
          GitLab configurado: {{ configStore.config.gitlab_url }}
        </div>
      </fieldset>

      <!-- Odoo -->
      <fieldset class="settings-group">
        <legend>Odoo</legend>
        <label class="field">
          <span>URL</span>
          <input type="url" v-model="configStore.config.odoo_url" placeholder="https://odoo.example.com" />
        </label>
        <label class="field">
          <span>Version</span>
          <select v-model="configStore.config.odoo_version">
            <option value="v11">v11 (XMLRPC)</option>
            <option value="v16">v16 (OAuth REST)</option>
          </select>
        </label>
        <label class="field">
          <span>Base de datos</span>
          <input type="text" v-model="configStore.config.odoo_db" placeholder="nombre_base_datos" />
        </label>
        <label class="field">
          <span>Usuario</span>
          <input type="text" v-model="configStore.config.odoo_username" placeholder="usuario@empresa.com" />
        </label>
        <div class="field">
          <span>Contrasena / Token</span>
          <div class="token-field">
            <input type="password" v-model="odooToken"
              :placeholder="configStore.config.odoo_token_stored ? '***** (guardado en keyring)' : 'Contrasena o API key'" />
            <button
              v-if="configStore.config.odoo_token_stored"
              type="button"
              class="btn btn-danger btn-sm"
              @click="clearOdooToken"
              title="Eliminar token"
            >
              Eliminar
            </button>
          </div>
        </div>
        <div class="field-hint" v-if="hasOdooConfig">
          Odoo configurado: {{ configStore.config.odoo_url }} ({{ configStore.config.odoo_version }})
        </div>
      </fieldset>

      <!-- Inteligencia Artificial -->
      <fieldset class="settings-group">
        <legend>Inteligencia Artificial</legend>
        <label class="field">
          <span>Proveedor</span>
          <select v-model="configStore.config.ai_provider">
            <option value="none">Desactivado</option>
            <option value="gemini">Google Gemini</option>
            <option value="claude">Anthropic Claude</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <div class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>API Key</span>
          <div class="token-field">
            <input type="password" v-model="aiToken"
              :placeholder="configStore.config.ai_api_key_stored ? '***** (guardada en keyring)' : 'API key del proveedor'" />
            <button
              v-if="configStore.config.ai_api_key_stored"
              type="button"
              class="btn btn-danger btn-sm"
              @click="clearAIToken"
              title="Eliminar API key"
            >
              Eliminar
            </button>
          </div>
        </div>
        <label class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>Perfil de usuario</span>
          <select v-model="configStore.config.ai_user_role">
            <option value="technical">Tecnico</option>
            <option value="functional">Funcional</option>
            <option value="other">Otro</option>
          </select>
        </label>
        <label class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>Contexto adicional</span>
          <textarea
            v-model="configStore.config.ai_custom_context"
            rows="2"
            placeholder="Ej: Desarrollador backend en equipo de facturacion Odoo, modulos account y sale"
            style="flex:1; background:var(--bg-card); color:var(--text-primary); border:1px solid var(--border); border-radius:4px; padding:6px 10px; font-size:13px; font-family:inherit; resize:vertical;"
          ></textarea>
        </label>
        <div class="field-hint" v-if="configStore.config.ai_provider !== 'none'">
          Las descripciones se generan automaticamente al cerrar cada bloque de actividad.
        </div>
      </fieldset>

      <!-- General -->
      <fieldset class="settings-group">
        <legend>General</legend>
        <label class="field">
          <span>Tema</span>
          <select v-model="configStore.config.theme">
            <option value="dark">Oscuro</option>
            <option value="light">Claro</option>
            <option value="system">Sistema</option>
          </select>
        </label>
        <label class="field">
          <span>Intervalo de refresco (s)</span>
          <input type="number" v-model.number="configStore.config.refresh_interval_seconds" min="30" max="3600" />
        </label>
        <label class="field">
          <span>Objetivo diario (horas)</span>
          <input type="number" v-model.number="configStore.config.daily_hour_target" min="1" max="24" step="0.5" />
        </label>
      </fieldset>

      <div v-if="daemonPushResult" class="daemon-push-banner" :class="daemonPushType">
        {{ daemonPushResult }}
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
        <span v-if="message" class="save-message" :class="messageType">{{ message }}</span>
      </div>
    </form>
  </div>
</template>

<style scoped>
.settings-form {
  max-width: 600px;
}

.settings-group {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.settings-group legend {
  font-weight: 600;
  font-size: 14px;
  padding: 0 8px;
  color: var(--accent);
}

.field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
}

.field > span:first-child {
  min-width: 140px;
  color: var(--text-secondary);
}

.field input, .field select {
  flex: 1;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
}

.token-field {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.token-field input {
  flex: 1;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
}

.field-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin: -4px 0 8px 152px;
  font-style: italic;
}

.connection-test {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.conn-ok {
  color: var(--success);
  font-size: 12px;
}

.conn-fail {
  color: var(--error);
  font-size: 12px;
}

.daemon-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.mode-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
}

.mode-badge.active {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
}

.mode-badge.silent {
  background: rgba(220, 220, 170, 0.15);
  color: var(--warning);
}

.mode-badge.paused {
  background: rgba(241, 76, 76, 0.15);
  color: var(--error);
}

.integration-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
}

.integration-badge.configured {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
}

.integration-badge.not-configured {
  background: rgba(162, 176, 180, 0.15);
  color: var(--text-secondary);
}

.info-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.daemon-push-banner {
  padding: 8px 14px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 12px;
}

.daemon-push-banner.success {
  background: rgba(78, 201, 176, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.daemon-push-banner.error {
  background: rgba(241, 76, 76, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
}

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

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-danger {
  background: transparent;
  color: var(--error);
  border: 1px solid var(--error);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(241, 76, 76, 0.1);
}

.btn:disabled {
  opacity: 0.5;
}

.save-message {
  font-size: 13px;
}

.save-message.success {
  color: var(--success);
}

.save-message.error {
  color: var(--error);
}
</style>
