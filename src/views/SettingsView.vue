<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const gitlabToken = ref('');
const odooToken = ref('');
const saving = ref(false);
const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const connectionResult = ref<'ok' | 'fail' | null>(null);

onMounted(() => {
  configStore.load();
});

async function saveConfig() {
  saving.value = true;
  message.value = '';
  try {
    await configStore.save(configStore.config);

    if (gitlabToken.value) {
      await configStore.setGitLabToken(gitlabToken.value);
      gitlabToken.value = '';
    }
    if (odooToken.value) {
      await configStore.setOdooToken(odooToken.value);
      odooToken.value = '';
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
          <input type="number" v-model.number="configStore.config.daemon_port" />
        </label>
        <div class="field">
          <span>Conexion</span>
          <div class="connection-test">
            <button type="button" class="btn btn-secondary btn-sm" @click="testConnection" :disabled="daemonStore.checking">
              {{ daemonStore.checking ? 'Probando...' : 'Probar conexion' }}
            </button>
            <span v-if="connectionResult === 'ok'" class="conn-ok">Conectado — {{ daemonStore.statusText }}</span>
            <span v-else-if="connectionResult === 'fail'" class="conn-fail">No se pudo conectar</span>
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
      </fieldset>

      <!-- GitLab -->
      <fieldset class="settings-group">
        <legend>GitLab</legend>
        <label class="field">
          <span>URL</span>
          <input type="url" v-model="configStore.config.gitlab_url" placeholder="https://gitlab.example.com" />
        </label>
        <label class="field">
          <span>Token</span>
          <input type="password" v-model="gitlabToken"
            :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
        </label>
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
          <input type="text" v-model="configStore.config.odoo_db" />
        </label>
        <label class="field">
          <span>Usuario</span>
          <input type="text" v-model="configStore.config.odoo_username" />
        </label>
        <label class="field">
          <span>Contrasena / Token</span>
          <input type="password" v-model="odooToken"
            :placeholder="configStore.config.odoo_token_stored ? '***** (guardado)' : 'Contrasena o API key'" />
        </label>
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
          <input type="number" v-model.number="configStore.config.refresh_interval_seconds" min="30" />
        </label>
        <label class="field">
          <span>Objetivo diario (horas)</span>
          <input type="number" v-model.number="configStore.config.daily_hour_target" min="1" max="24" step="0.5" />
        </label>
      </fieldset>

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

.field span {
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

.info-text {
  font-size: 12px;
  color: var(--text-secondary);
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
