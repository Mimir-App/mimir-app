<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';
import GeneralTab from '../components/settings/GeneralTab.vue';
import CaptureTab from '../components/settings/CaptureTab.vue';
import OdooTab from '../components/settings/OdooTab.vue';
import GitLabTab from '../components/settings/GitLabTab.vue';
import AITab from '../components/settings/AITab.vue';
import GoogleTab from '../components/settings/GoogleTab.vue';
import ServicesTab from '../components/settings/ServicesTab.vue';
import NotificationsTab from '../components/settings/NotificationsTab.vue';

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const saving = ref(false);
const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const integrationStatus = ref<Record<string, unknown>>({});
const daemonPushResult = ref<string | null>(null);
const daemonPushType = ref<'success' | 'error'>('success');
const activeTab = ref('general');
const googleTabRef = ref<InstanceType<typeof GoogleTab> | null>(null);

const tabs = computed(() => [
  { id: 'general', label: 'General', enabled: true },
  { id: 'capture', label: 'Captura', enabled: true },
  { id: 'odoo', label: 'Odoo', enabled: true },
  { id: 'vcs', label: 'Repositorios', enabled: true },
  { id: 'ai', label: 'IA', enabled: true },
  { id: 'google', label: 'Google', enabled: true },
  { id: 'services', label: 'Servicios', enabled: true },
  { id: 'notifications', label: 'Notificaciones', enabled: true },
].filter(t => t.enabled));

onMounted(async () => {
  await configStore.load();
  await daemonStore.captureHealthCheck();
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

function handleMessage(text: string, type: 'success' | 'error') {
  message.value = text;
  messageType.value = type;
}

// Google Calendar state from GoogleTab (for ServicesTab)
const googleCalendarConnected = computed(() => googleTabRef.value?.googleCalendarConnected ?? false);
const authorizingGoogle = computed(() => googleTabRef.value?.authorizingGoogle ?? false);

function handleAuthorizeGoogle() {
  googleTabRef.value?.authorizeGoogle();
}

function handleDisconnectGoogle() {
  googleTabRef.value?.disconnectGoogle();
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

      <GeneralTab v-show="activeTab === 'general'" />
      <CaptureTab v-show="activeTab === 'capture'" />
      <OdooTab
        v-show="activeTab === 'odoo'"
        :integration-status="integrationStatus"
        @refresh-status="refreshIntegrationStatus"
        @message="handleMessage"
      />
      <GitLabTab
        v-show="activeTab === 'vcs'"
        :integration-status="integrationStatus"
        @refresh-status="refreshIntegrationStatus"
        @message="handleMessage"
      />
      <AITab
        v-show="activeTab === 'ai'"
        @message="handleMessage"
      />
      <GoogleTab
        ref="googleTabRef"
        v-show="activeTab === 'google'"
      />
      <ServicesTab
        v-show="activeTab === 'services'"
        :integration-status="integrationStatus"
        :google-calendar-connected="googleCalendarConnected"
        :authorizing-google="authorizingGoogle"
        @message="handleMessage"
        @authorize-google="handleAuthorizeGoogle"
        @disconnect-google="handleDisconnectGoogle"
      />
      <NotificationsTab v-show="activeTab === 'notifications'" />

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

.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn:disabled { opacity: 0.5; }

.save-msg { font-size: 13px; }
.save-msg.success { color: var(--success); }
.save-msg.error { color: var(--error); }
</style>
