<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue';
import { useRouter, onBeforeRouteLeave } from 'vue-router';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';
import GeneralTab from '../components/settings/GeneralTab.vue';
import CaptureTab from '../components/settings/CaptureTab.vue';
import OdooTab from '../components/settings/OdooTab.vue';
import GitLabTab from '../components/settings/GitLabTab.vue';
import AITab from '../components/settings/AITab.vue';
import AgentTab from '../components/settings/AgentTab.vue';
import GoogleTab from '../components/settings/GoogleTab.vue';
import ServicesTab from '../components/settings/ServicesTab.vue';
import NotificationsTab from '../components/settings/NotificationsTab.vue';
import ModalDialog from '../components/shared/ModalDialog.vue';

const router = useRouter();
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

// --- Dirty check: detectar cambios sin guardar ---
const savedSnapshot = ref('');
const showUnsavedModal = ref(false);
const dirty = ref(false);
// Acción pendiente: cambio de tab o navegación a ruta
const pendingAction = ref<{ type: 'tab'; id: string } | { type: 'route'; path: string } | null>(null);

function takeSnapshot() {
  savedSnapshot.value = JSON.stringify(configStore.config);
  dirty.value = false;
}

watch(() => JSON.stringify(configStore.config), (current) => {
  if (!savedSnapshot.value) return;
  dirty.value = current !== savedSnapshot.value;
});

function switchTab(tabId: string) {
  if (tabId === activeTab.value) return;
  if (dirty.value) {
    pendingAction.value = { type: 'tab', id: tabId };
    showUnsavedModal.value = true;
  } else {
    activeTab.value = tabId;
  }
}

// Guard de navegación: bloquear salida si hay cambios sin guardar
onBeforeRouteLeave((to) => {
  if (dirty.value) {
    pendingAction.value = { type: 'route', path: to.path };
    showUnsavedModal.value = true;
    return false; // bloquear navegación
  }
});

function discardAndApply() {
  const restored = JSON.parse(savedSnapshot.value);
  Object.assign(configStore.config, restored);
  showUnsavedModal.value = false;
  const action = pendingAction.value;
  pendingAction.value = null;
  if (action?.type === 'tab') {
    activeTab.value = action.id;
  } else if (action?.type === 'route') {
    router.push(action.path);
  }
}

async function saveAndApply() {
  showUnsavedModal.value = false;
  await saveConfig();
  const action = pendingAction.value;
  pendingAction.value = null;
  if (action?.type === 'tab') {
    activeTab.value = action.id;
  } else if (action?.type === 'route') {
    router.push(action.path);
  }
}

const tabs = computed(() => [
  { id: 'general', label: 'General', enabled: true },
  { id: 'capture', label: 'Captura', enabled: true },
  { id: 'odoo', label: 'Odoo', enabled: true },
  { id: 'vcs', label: 'Repositorios', enabled: true },
  { id: 'ai', label: 'IA', enabled: true },
  { id: 'agent', label: 'Agente', enabled: true },
  { id: 'google', label: 'Google', enabled: true },
  { id: 'services', label: 'Servicios', enabled: true },
  { id: 'notifications', label: 'Notificaciones', enabled: true },
].filter(t => t.enabled));

onMounted(async () => {
  await configStore.load();
  takeSnapshot();
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
    takeSnapshot();
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
          @click="switchTab(tab.id)"
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
      <AgentTab
        v-show="activeTab === 'agent'"
        @message="handleMessage"
      />
      <GoogleTab
        ref="googleTabRef"
        v-show="activeTab === 'google'"
        @message="handleMessage"
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

    <ModalDialog title="Cambios sin guardar" :open="showUnsavedModal" @close="showUnsavedModal = false">
      <p class="unsaved-text">Hay cambios sin guardar en esta pestana. ¿Que quieres hacer?</p>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="discardAndApply">Descartar</button>
        <button type="button" class="btn btn-primary" @click="saveAndApply">Guardar y cambiar</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
@import '../assets/settings-shared.css';

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

.push-banner.success { background: var(--success-soft); border: 1px solid var(--success); color: var(--success); }
.push-banner.error { background: var(--error-soft); border: 1px solid var(--error); color: var(--error); }

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

.unsaved-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
