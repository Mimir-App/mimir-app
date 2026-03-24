<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import { api } from '../../lib/api';
import IntegrationCard from '../shared/IntegrationCard.vue';
import ModalDialog from '../shared/ModalDialog.vue';
import SettingRow from './SettingRow.vue';

const emit = defineEmits<{
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const showGoogleSetupModal = ref(false);
const googleCalendarConnected = ref(false);
const authorizingGoogle = ref(false);

async function checkGoogleCalendarStatus() {
  try {
    const result = await api.getGoogleCalendarStatus() as { configured: boolean; connected: boolean };
    googleCalendarConnected.value = result.connected;
  } catch {
    googleCalendarConnected.value = false;
    emit('message', 'Error comprobando estado de Google Calendar', 'error');
  }
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
        if (googleCalendarConnected.value) {
          emit('message', 'Google Calendar conectado', 'success');
        }
      }
    }, 3000);
  } catch (e) {
    authorizingGoogle.value = false;
    emit('message', `Error autorizando Google: ${e}`, 'error');
  }
}

async function disconnectGoogle() {
  try {
    await api.disconnectGoogleCalendar();
    googleCalendarConnected.value = false;
    emit('message', 'Google Calendar desconectado', 'success');
  } catch (e) {
    emit('message', `Error desconectando Google: ${e}`, 'error');
  }
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
        <SettingRow label="Autorizaciones"><span>Google Calendar (lectura)</span></SettingRow>
        <SettingRow label="Servicios"><span class="service-chip active">Calendar — Deteccion de reuniones</span></SettingRow>
        <div style="margin-top: 12px;">
          <button type="button" class="btn btn-secondary btn-sm" @click="showGoogleSetupModal = true">Editar credenciales</button>
        </div>
      </template>
    </IntegrationCard>

    <ModalDialog title="Credenciales Google OAuth2" :open="showGoogleSetupModal" @close="showGoogleSetupModal = false">
      <SettingRow label="Client ID">
        <input type="text" v-model="configStore.config.google_client_id" placeholder="123456789.apps.googleusercontent.com" />
      </SettingRow>
      <SettingRow label="Client Secret">
        <input type="password" v-model="configStore.config.google_client_secret" placeholder="GOCSPX-..." />
      </SettingRow>
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

.session-detail { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }

.service-chip { font-size: 12px; padding: 4px 10px; border-radius: 4px; background: var(--bg-card); border: 1px solid var(--border); }
.service-chip.active { border-color: var(--success); color: var(--success); }

.google-help { margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 6px; font-size: 13px; text-align: left; }
.google-help ol { margin: 8px 0 0 20px; }
.google-help li { margin-bottom: 4px; }
.google-help code { background: var(--bg-card); padding: 2px 4px; border-radius: 3px; font-size: 12px; }
</style>
