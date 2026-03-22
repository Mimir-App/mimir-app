<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import { api } from '../../lib/api';
import IntegrationCard from '../shared/IntegrationCard.vue';
import ModalDialog from '../shared/ModalDialog.vue';

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const showGoogleSetupModal = ref(false);
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
  if (daemonStore.connected) {
    await checkGoogleCalendarStatus();
  }
});

defineExpose({ googleCalendarConnected, authorizingGoogle, authorizeGoogle, disconnectGoogle, checkGoogleCalendarStatus });
</script>

<template>
  <div class="tab-content">
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

.settings-table input {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.session-detail { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }

.service-chip { font-size: 12px; padding: 4px 10px; border-radius: 4px; background: var(--bg-card); border: 1px solid var(--border); }
.service-chip.active { border-color: var(--success); color: var(--success); }

.google-help { margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 6px; font-size: 13px; text-align: left; }
.google-help ol { margin: 8px 0 0 20px; }
.google-help li { margin-bottom: 4px; }
.google-help code { background: var(--bg-card); padding: 2px 4px; border-radius: 3px; font-size: 12px; }

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
.btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-hover); }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: rgba(241, 76, 76, 0.1); }
.btn:disabled { opacity: 0.5; }
</style>
