<script setup lang="ts">
import { ref, computed } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import HelpTooltip from '../shared/HelpTooltip.vue';
import IntegrationCard from '../shared/IntegrationCard.vue';
import ModalDialog from '../shared/ModalDialog.vue';

const props = defineProps<{
  integrationStatus: Record<string, unknown>;
}>();

const emit = defineEmits<{
  'refresh-status': [];
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const gitlabToken = ref('');
const showGitlabModal = ref(false);
const testingGitlab = ref(false);
const gitlabTestResult = ref<'ok' | 'fail' | null>(null);
const gitlabTestMessage = ref('');

const gitlabIntegrationConfigured = computed((): boolean => {
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
    if (result.status === 'ok' && gitlabIntegrationConfigured.value) {
      gitlabTestResult.value = 'ok'; gitlabTestMessage.value = 'Conectado a GitLab';
    } else { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = 'No se pudo conectar'; }
  } catch (e) { gitlabTestResult.value = 'fail'; gitlabTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingGitlab.value = false; }
}
</script>

<template>
  <div class="tab-content">
    <IntegrationCard
      name="GitLab"
      icon="G"
      description="Conecta con tu instancia GitLab para ver issues y merge requests asignadas."
      :connected="gitlabIntegrationConfigured"
      connect-label="Configurar GitLab"
      disconnect-label="Desconectar"
      @connect="showGitlabModal = true"
      @disconnect="clearGitLabToken"
    >
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
        <div style="margin-top: 12px;">
          <button type="button" class="btn btn-secondary btn-sm" @click="showGitlabModal = true">Editar configuracion</button>
        </div>
      </template>
    </IntegrationCard>

    <ModalDialog title="Configurar GitLab" :open="showGitlabModal" @close="showGitlabModal = false">
      <table class="settings-table">
        <tbody>
          <tr>
            <td class="label-cell">URL</td>
            <td><input type="url" v-model="configStore.config.gitlab_url" placeholder="https://gitlab.example.com" /></td>
          </tr>
          <tr>
            <td class="label-cell">Token</td>
            <td>
              <div class="token-field">
                <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Personal Access Token'" />
              </div>
            </td>
          </tr>
          <tr>
            <td></td>
            <td>
              <div class="connection-test">
                <button type="button" class="btn btn-secondary btn-sm" @click="testGitlabConnection" :disabled="testingGitlab">
                  {{ testingGitlab ? 'Probando...' : 'Probar conexion' }}
                </button>
                <span v-if="gitlabTestResult === 'ok'" class="conn-ok">{{ gitlabTestMessage }}</span>
                <span v-else-if="gitlabTestResult === 'fail'" class="conn-fail">{{ gitlabTestMessage }}</span>
              </div>
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
        Mapeo de prioridad de labels: asigna un peso (0-100) a cada label de GitLab para influir en el scoring de issues.
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
