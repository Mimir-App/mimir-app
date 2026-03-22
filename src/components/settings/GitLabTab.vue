<script setup lang="ts">
import { ref, computed } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import HelpTooltip from '../shared/HelpTooltip.vue';
import IntegrationCard from '../shared/IntegrationCard.vue';
import ModalDialog from '../shared/ModalDialog.vue';
import SourceIcon from '../shared/SourceIcon.vue';

const props = defineProps<{
  integrationStatus: Record<string, unknown>;
}>();

const emit = defineEmits<{
  'refresh-status': [];
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();
const daemonStore = useDaemonStore();

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
const testingGithub = ref(false);
const githubTestResult = ref<'ok' | 'fail' | null>(null);
const githubTestMessage = ref('');

const githubConfigured = computed((): boolean => {
  const github = props.integrationStatus?.github;
  return github && typeof github === 'object' ? Boolean((github as Record<string, unknown>).configured) : false;
});

function openGithubModal() {
  githubToken.value = '';
  showGithubModal.value = true;
}

async function confirmGithubModal() {
  if (githubToken.value) {
    await configStore.setGitHubToken(githubToken.value);
    githubToken.value = '';
  }
  await configStore.save(configStore.config);
  showGithubModal.value = false;
  emit('message', 'Configuracion GitHub guardada', 'success');
}

async function clearGitHubToken() {
  try {
    await configStore.deleteGitHubToken();
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
        <table class="settings-table">
          <tbody>
            <tr>
              <td class="label-cell">Servidor</td>
              <td>github.com</td>
              <td class="label-cell">Auth</td>
              <td>Personal Access Token</td>
            </tr>
          </tbody>
        </table>
      </template>
    </IntegrationCard>

    <!-- Modal GitLab -->
    <ModalDialog title="Configurar GitLab" :open="showGitlabModal" showFooter @close="showGitlabModal = false" @confirm="confirmGitlabModal">
      <table class="settings-table">
        <tbody>
          <tr>
            <td class="label-cell">URL</td>
            <td><input type="url" v-model="gitlabUrl" placeholder="https://gitlab.example.com" /></td>
          </tr>
          <tr>
            <td class="label-cell">Token</td>
            <td>
              <div class="token-field">
                <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </ModalDialog>

    <!-- Modal GitHub -->
    <ModalDialog title="Configurar GitHub" :open="showGithubModal" showFooter @close="showGithubModal = false" @confirm="confirmGithubModal">
      <table class="settings-table">
        <tbody>
          <tr>
            <td class="label-cell">Token</td>
            <td>
              <div class="token-field">
                <input type="password" v-model="githubToken" :placeholder="configStore.config.github_token_stored ? '***** (guardado)' : 'Personal Access Token (classic o fine-grained)'" />
              </div>
            </td>
          </tr>
          <tr>
            <td></td>
            <td>
              <p class="token-hint">Permisos necesarios: <code>repo</code>, <code>read:org</code>, <code>notifications</code></p>
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
        Mapeo de prioridad de labels: asigna un peso (0-100) a cada label para influir en el scoring de issues.
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

.settings-table input,
.settings-table select {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.inline-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inline-field input {
  flex: 1;
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
.btn-danger:hover:not(:disabled) { background: rgba(241, 76, 76, 0.1); }
.btn:disabled { opacity: 0.5; }
</style>
