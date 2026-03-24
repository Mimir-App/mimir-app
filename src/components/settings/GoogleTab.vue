<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useDaemonStore } from '../../stores/daemon';
import { api } from '../../lib/api';
import IntegrationCard from '../shared/IntegrationCard.vue';
import SettingRow from './SettingRow.vue';

const emit = defineEmits<{
  'message': [text: string, type: 'success' | 'error'];
}>();

const daemonStore = useDaemonStore();
const googleCalendarConnected = ref(false);
const authorizingGoogle = ref(false);
const testing = ref(false);
const testResult = ref<'ok' | 'fail' | null>(null);
const testMessage = ref('');

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
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('plugin:opener|open_url', { url: result.url });
    } catch {
      window.open(result.url, '_blank');
    }
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

async function testGoogle() {
  testing.value = true;
  testResult.value = null;
  try {
    const result = await api.getGoogleCalendarStatus() as { configured: boolean; connected: boolean };
    testResult.value = result.connected ? 'ok' : 'fail';
    testMessage.value = result.connected ? 'Conexion activa' : 'Token expirado';
  } catch {
    testResult.value = 'fail';
    testMessage.value = 'Error de conexion';
  } finally {
    testing.value = false;
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
      description="Conecta tu cuenta de Google para detectar reuniones y enriquecer los bloques de actividad."
      :connected="googleCalendarConnected"
      :connect-label="authorizingGoogle ? 'Esperando autorizacion...' : 'Iniciar sesion con Google'"
      disconnect-label="Cerrar sesion"
      hide-edit
      :testing="testing"
      :test-result="testResult"
      :test-message="testMessage"
      @connect="authorizeGoogle()"
      @disconnect="disconnectGoogle"
      @test="testGoogle"
    >
      <template #status>
        <p class="session-detail">Cuenta autorizada con acceso a los servicios configurados</p>
      </template>
      <template #details>
        <SettingRow label="Autorizaciones"><span>Google Calendar (lectura)</span></SettingRow>
        <SettingRow label="Servicios"><span class="service-chip active">Calendar — Deteccion de reuniones</span></SettingRow>
      </template>
    </IntegrationCard>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}

.session-detail { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }

.service-chip { font-size: 12px; padding: 4px 10px; border-radius: 4px; background: var(--bg-card); border: 1px solid var(--border); }
.service-chip.active { border-color: var(--success); color: var(--success); }

</style>
