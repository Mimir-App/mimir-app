<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import { api } from '../../lib/api';
import IntegrationCard from '../shared/IntegrationCard.vue';
import ModalDialog from '../shared/ModalDialog.vue';
import SourceIcon from '../shared/SourceIcon.vue';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';
import { X } from 'lucide-vue-next';

const props = defineProps<{
  integrationStatus: Record<string, unknown>;
}>();

const emit = defineEmits<{
  'refresh-status': [];
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();
const daemonStore = useDaemonStore();

onUnmounted(() => {
  if (oauthPollTimer) clearInterval(oauthPollTimer);
});

// --- GitLab ---
const gitlabToken = ref('');
const gitlabUrl = ref('');
const showGitlabModal = ref(false);
const testingGitlab = ref(false);
const gitlabTestResult = ref<'ok' | 'fail' | null>(null);
const gitlabTestMessage = ref('');

const gitlabConfigured = computed((): boolean => {
  const gitlab = props.integrationStatus?.gitlab;
  return gitlab && typeof gitlab === 'object' ? Boolean((gitlab as Record<string, unknown>).configured) : false;
});

async function clearGitLabToken() {
  try {
    await configStore.deleteGitLabToken();
    await configStore.pushToDaemon();
    emit('refresh-status');
    emit('message', 'Token GitLab eliminado', 'success');
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  }
}

async function testGitlabConnection() {
  testingGitlab.value = true; gitlabTestResult.value = null; gitlabTestMessage.value = '';
  try {
    if (gitlabToken.value) { await configStore.setGitLabToken(gitlabToken.value); gitlabToken.value = ''; }
    await configStore.save(configStore.config);
    if (!daemonStore.connected) { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = 'Servidor API no conectado'; return; }
    const result = await configStore.pushToDaemon();
    emit('refresh-status');
    if (result.status === 'ok' && gitlabConfigured.value) {
      gitlabTestResult.value = 'ok'; gitlabTestMessage.value = 'Conectado a GitLab';
    } else { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = 'No se pudo conectar'; }
  } catch (e) { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingGitlab.value = false; }
}

function openGitlabModal() {
  gitlabUrl.value = configStore.config.gitlab_url;
  gitlabToken.value = '';
  showGitlabModal.value = true;
}

async function confirmGitlabModal() {
  configStore.config.gitlab_url = gitlabUrl.value;
  if (gitlabToken.value) {
    await configStore.setGitLabToken(gitlabToken.value);
    gitlabToken.value = '';
  }
  await configStore.save(configStore.config);
  showGitlabModal.value = false;
  emit('message', 'Configuracion GitLab guardada', 'success');
}

// --- GitHub ---
const githubToken = ref('');
const showGithubModal = ref(false);
const githubAuthTab = ref<'oauth' | 'pat'>('oauth');
const testingGithub = ref(false);
const githubTestResult = ref<'ok' | 'fail' | null>(null);
const githubTestMessage = ref('');

// OAuth Device Flow state
const oauthLoading = ref(false);
const oauthUserCode = ref('');
const oauthVerificationUri = ref('');
const oauthDeviceCode = ref('');
const oauthPolling = ref(false);
const oauthStatus = ref('');
let oauthPollTimer: ReturnType<typeof setInterval> | null = null;

const githubConfigured = computed((): boolean => {
  const github = props.integrationStatus?.github;
  return github && typeof github === 'object' ? Boolean((github as Record<string, unknown>).configured) : false;
});

function openGithubModal() {
  githubToken.value = '';
  githubAuthTab.value = 'oauth';
  oauthUserCode.value = '';
  oauthStatus.value = '';
  oauthPolling.value = false;
  stopOAuthPolling();
  showGithubModal.value = true;
}

async function startOAuthFlow() {
  oauthLoading.value = true;
  oauthStatus.value = '';
  try {
    const result = await api.githubOAuthStart();
    if (result.error) {
      oauthStatus.value = `Error: ${result.error}`;
      return;
    }
    oauthUserCode.value = result.user_code;
    oauthVerificationUri.value = result.verification_uri;
    oauthDeviceCode.value = result.device_code;
    oauthStatus.value = 'waiting';

    // Abrir el navegador
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_url', { url: result.verification_uri });
    } catch {
      // Fallback: el usuario abrirá manualmente
    }

    // Iniciar polling (añadir 1s de margen para evitar slow_down)
    const interval = ((result.interval || 5) + 1) * 1000;
    oauthPolling.value = true;
    oauthPollTimer = setInterval(() => pollOAuth(), interval);
  } catch (e) {
    oauthStatus.value = `Error: ${e}`;
  } finally {
    oauthLoading.value = false;
  }
}

async function pollOAuth() {
  if (!oauthDeviceCode.value) return;
  try {
    const result = await api.githubOAuthPoll(oauthDeviceCode.value);
    console.log('[OAuth poll]', JSON.stringify(result));
    if (result.status === 'complete' && result.access_token) {
      stopOAuthPolling();
      oauthStatus.value = 'complete';
      // Guardar token en keyring
      await configStore.setGitHubToken(result.access_token);
      await configStore.save(configStore.config);
      emit('refresh-status');
      emit('message', 'GitHub conectado via OAuth', 'success');
      showGithubModal.value = false;
    } else if (result.status === 'expired') {
      stopOAuthPolling();
      oauthStatus.value = 'El código ha expirado. Inténtalo de nuevo.';
    } else if (result.status === 'error') {
      stopOAuthPolling();
      oauthStatus.value = `Error: ${result.error}`;
    } else if (result.status === 'slow_down') {
      // Reiniciar timer con intervalo mayor
      stopOAuthPolling();
      const newInterval = (result.interval || 10) * 1000;
      oauthPolling.value = true;
      oauthPollTimer = setInterval(() => pollOAuth(), newInterval);
    }
    // 'pending' → seguir polling con intervalo actual
  } catch {
    // Error de red → seguir intentando
  }
}

function stopOAuthPolling() {
  oauthPolling.value = false;
  if (oauthPollTimer) { clearInterval(oauthPollTimer); oauthPollTimer = null; }
}

async function confirmGithubModal() {
  if (githubToken.value) {
    await configStore.setGitHubToken(githubToken.value);
    githubToken.value = '';
  }
  await configStore.save(configStore.config);
  showGithubModal.value = false;
  emit('message', 'Configuración GitHub guardada', 'success');
}

async function clearGitHubToken() {
  stopOAuthPolling();
  try {
    await configStore.deleteGitHubToken();
    await configStore.pushToDaemon();
    emit('refresh-status');
    emit('message', 'Token GitHub eliminado', 'success');
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  }
}

async function testGithubConnection() {
  testingGithub.value = true; githubTestResult.value = null; githubTestMessage.value = '';
  try {
    if (githubToken.value) { await configStore.setGitHubToken(githubToken.value); githubToken.value = ''; }
    await configStore.save(configStore.config);
    if (!daemonStore.connected) { githubTestResult.value = 'fail'; githubTestMessage.value = 'Servidor API no conectado'; return; }
    const result = await configStore.pushToDaemon();
    emit('refresh-status');
    if (result.status === 'ok' && githubConfigured.value) {
      githubTestResult.value = 'ok'; githubTestMessage.value = 'Conectado a GitHub';
    } else { githubTestResult.value = 'fail'; githubTestMessage.value = 'No se pudo conectar'; }
  } catch (e) { githubTestResult.value = 'fail'; githubTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingGithub.value = false; }
}
</script>

<template>
  <div class="tab-content">
    <!-- GitLab -->
    <IntegrationCard
      name="GitLab"
      description="Issues, merge requests y scoring desde tu instancia GitLab."
      :connected="gitlabConfigured"
      connect-label="Configurar GitLab"
      :testing="testingGitlab"
      :test-result="gitlabTestResult"
      :test-message="gitlabTestMessage"
      @connect="openGitlabModal"
      @edit="openGitlabModal"
      @test="testGitlabConnection"
      @disconnect="clearGitLabToken"
    >
      <template #icon><SourceIcon source="gitlab" :size="24" /></template>
      <template #status>
        <p class="session-detail">{{ configStore.config.gitlab_url.replace(/^https?:\/\//, '') }}</p>
      </template>
      <template #details>
        <SettingRow label="Servidor"><span>{{ configStore.config.gitlab_url }}</span></SettingRow>
        <SettingRow label="Auth"><span>Personal Access Token</span></SettingRow>
      </template>
    </IntegrationCard>

    <!-- GitHub -->
    <IntegrationCard
      name="GitHub"
      description="Issues, pull requests y notificaciones desde GitHub."
      :connected="githubConfigured"
      connect-label="Configurar GitHub"
      :testing="testingGithub"
      :test-result="githubTestResult"
      :test-message="githubTestMessage"
      @connect="openGithubModal"
      @edit="openGithubModal"
      @test="testGithubConnection"
      @disconnect="clearGitHubToken"
    >
      <template #icon><SourceIcon source="github" :size="24" /></template>
      <template #status>
        <p class="session-detail">github.com</p>
      </template>
      <template #details>
        <SettingRow label="Servidor"><span>github.com</span></SettingRow>
        <SettingRow label="Auth"><span>{{ githubConfigured ? 'Token configurado' : 'No configurado' }}</span></SettingRow>
      </template>
    </IntegrationCard>

    <!-- Modal GitLab -->
    <ModalDialog title="Configurar GitLab" :open="showGitlabModal" showFooter @close="showGitlabModal = false" @confirm="confirmGitlabModal">
      <SettingRow label="URL" fullWidth>
        <input type="url" v-model="gitlabUrl" placeholder="https://gitlab.example.com" />
      </SettingRow>
      <SettingRow label="Token" fullWidth>
        <div class="token-field">
          <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
        </div>
      </SettingRow>
    </ModalDialog>

    <!-- Modal GitHub -->
    <ModalDialog title="Configurar GitHub" :open="showGithubModal" :showFooter="githubAuthTab === 'pat'" @close="showGithubModal = false; stopOAuthPolling()" @confirm="confirmGithubModal">
      <div class="github-auth-tabs">
        <button class="auth-tab" :class="{ active: githubAuthTab === 'oauth' }" @click="githubAuthTab = 'oauth'; stopOAuthPolling()">OAuth (recomendado)</button>
        <button class="auth-tab" :class="{ active: githubAuthTab === 'pat' }" @click="githubAuthTab = 'pat'; stopOAuthPolling()">Token manual</button>
      </div>

      <!-- OAuth Tab -->
      <div v-if="githubAuthTab === 'oauth'" class="oauth-flow">
        <template v-if="!oauthUserCode">
          <p class="oauth-description">Autoriza Mimir en tu cuenta de GitHub. Se abrirá una ventana del navegador para completar el proceso.</p>
          <button class="btn-oauth" @click="startOAuthFlow" :disabled="oauthLoading || !daemonStore.connected">
            <SourceIcon source="github" :size="18" />
            {{ oauthLoading ? 'Conectando...' : 'Conectar con GitHub' }}
          </button>
          <p v-if="!daemonStore.connected" class="oauth-hint error">Servidor API no conectado</p>
          <p v-if="oauthStatus && oauthStatus !== 'waiting'" class="oauth-hint error">{{ oauthStatus }}</p>
        </template>

        <template v-else>
          <div class="oauth-code-box">
            <p class="oauth-instruction">Introduce este código en GitHub:</p>
            <div class="oauth-code">{{ oauthUserCode }}</div>
            <p class="oauth-url">
              <a :href="oauthVerificationUri" target="_blank" rel="noopener">{{ oauthVerificationUri }}</a>
            </p>
          </div>
          <div v-if="oauthPolling" class="oauth-waiting">
            <span class="oauth-spinner"></span>
            Esperando autorización...
          </div>
          <p v-if="oauthStatus === 'complete'" class="oauth-hint success">Conectado correctamente</p>
          <p v-if="oauthStatus && !['waiting', 'complete'].includes(oauthStatus)" class="oauth-hint error">{{ oauthStatus }}</p>
        </template>
      </div>

      <!-- PAT Tab -->
      <div v-if="githubAuthTab === 'pat'">
        <SettingRow label="Token" fullWidth>
          <div class="token-field">
            <input type="password" v-model="githubToken" :placeholder="configStore.config.github_token_stored ? '***** (guardado)' : 'Personal Access Token (classic o fine-grained)'" />
          </div>
        </SettingRow>
        <p class="token-hint">Permisos necesarios: <code>repo</code>, <code>read:org</code>, <code>notifications</code></p>
      </div>
    </ModalDialog>

    <!-- Scoring: prioridad de labels + notas -->
    <SettingGroup title="Scoring de issues">
      <SettingRow label="Comentarios en detalle de issue" help="Numero de comentarios recientes a mostrar al abrir el detalle de una issue.">
        <input type="number" v-model.number="configStore.config.issue_notes_count" min="1" max="20" />
      </SettingRow>

      <p class="section-hint" style="margin-top: 16px;">
        Mapeo de prioridad de labels: asigna un peso (0-100) a cada label para influir en el scoring de issues.
      </p>
      <table class="priority-labels-table">
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
              <button type="button" class="btn btn-danger btn-sm" @click="configStore.config.gitlab_priority_labels.splice(idx, 1)" aria-label="Eliminar regla">
                <X :size="12" :stroke-width="2" />
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
    </SettingGroup>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}

.token-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.token-field input {
  flex: 1;
}

.token-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 0;
}

.token-hint code {
  background: var(--bg-card);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 10px;
}

.connection-test {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conn-ok { color: var(--success); font-size: 12px; }
.conn-fail { color: var(--error); font-size: 12px; }

.session-detail { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }

.section-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }

.priority-labels-table {
  width: 100%;
  border-collapse: collapse;
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
  padding: 8px 10px;
  vertical-align: middle;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
}

.priority-labels-table tr:last-child td {
  border-bottom: none;
}

.priority-labels-table input {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.empty-hint {
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
  padding: 16px 10px !important;
}

.action-cell { white-space: nowrap; }

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
.btn-danger:hover:not(:disabled) { background: var(--error-soft); }
.btn:disabled { opacity: 0.5; }

/* GitHub OAuth tabs */
.github-auth-tabs {
  display: flex;
  gap: 0;
  margin-bottom: var(--space-4, 16px);
  border-bottom: 2px solid var(--border);
}

.auth-tab {
  flex: 1;
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.auth-tab:hover {
  color: var(--text-primary);
}

.auth-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* OAuth flow */
.oauth-flow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3, 12px);
  padding: var(--space-4, 16px) 0;
}

.oauth-description {
  font-size: var(--text-sm, 13px);
  color: var(--text-secondary);
  text-align: center;
  max-width: 320px;
  line-height: 1.5;
}

.btn-oauth {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-3, 12px) var(--space-6, 24px);
  border-radius: var(--radius-lg, 12px);
  background: var(--text-primary);
  color: var(--bg-primary);
  font-size: var(--text-sm, 13px);
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-oauth:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-oauth:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.oauth-code-box {
  text-align: center;
  padding: var(--space-4, 16px);
  background: var(--bg-card, #383840);
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--border);
  width: 100%;
}

.oauth-instruction {
  font-size: var(--text-sm, 13px);
  color: var(--text-secondary);
  margin-bottom: var(--space-2, 8px);
}

.oauth-code {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
  letter-spacing: 0.15em;
  color: var(--accent);
  padding: var(--space-2, 8px) 0;
  user-select: all;
}

.oauth-url {
  font-size: var(--text-xs, 11px);
  margin-top: var(--space-2, 8px);
}

.oauth-url a {
  color: var(--accent);
  text-decoration: none;
}

.oauth-url a:hover {
  text-decoration: underline;
}

.oauth-waiting {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--text-sm, 13px);
  color: var(--text-secondary);
}

.oauth-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: oauth-spin 0.8s linear infinite;
}

@keyframes oauth-spin {
  to { transform: rotate(360deg); }
}

.oauth-hint {
  font-size: var(--text-xs, 11px);
  text-align: center;
}

.oauth-hint.error {
  color: var(--error);
}

.oauth-hint.success {
  color: var(--success);
}
</style>
