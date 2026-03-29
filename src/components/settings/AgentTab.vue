<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useConfigStore } from '../../stores/config';
import { api } from '../../lib/api';
import CustomSelect from '../shared/CustomSelect.vue';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  FolderGit2,
  Trash2,
} from 'lucide-vue-next';

const emit = defineEmits<{
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();

// --- CLI status ---
const cliChecking = ref(false);
const cliInstalled = ref<boolean | null>(null);
const cliAuthenticated = ref<boolean | null>(null);
const cliVersion = ref<string | null>(null);
const cliAccount = ref<string | null>(null);

async function checkCli() {
  cliChecking.value = true;
  try {
    const result = await api.checkClaudeCli();
    cliInstalled.value = result.installed;
    cliAuthenticated.value = result.authenticated;
    cliVersion.value = result.version;
    cliAccount.value = result.account;
  } catch {
    cliInstalled.value = false;
    cliAuthenticated.value = false;
  } finally {
    cliChecking.value = false;
  }
}

// --- Repo ---
const repoUrl = ref('');
const cloning = ref(false);
const repoInfo = ref<{
  exists: boolean;
  path?: string;
  remote_url?: string;
  last_commit?: string;
  agent_count?: number;
  has_claude_md?: boolean;
  has_claude_dir?: boolean;
} | null>(null);
const updating = ref(false);

async function loadRepoInfo() {
  try {
    repoInfo.value = await api.getAgentsRepoInfo();
    if (repoInfo.value.exists && repoInfo.value.remote_url) {
      repoUrl.value = repoInfo.value.remote_url;
    }
  } catch {
    repoInfo.value = null;
  }
}

async function cloneRepo() {
  if (!repoUrl.value.trim()) return;
  cloning.value = true;
  try {
    const result = await api.cloneAgentsRepo(repoUrl.value.trim());
    configStore.config.agents_repo_url = repoUrl.value.trim();
    configStore.config.agents_repo_enabled = true;
    emit('message', `Repositorio clonado (${result.agent_count} agentes encontrados)`, 'success');
    await loadRepoInfo();
  } catch (e) {
    emit('message', `Error clonando: ${e}`, 'error');
  } finally {
    cloning.value = false;
  }
}

async function updateRepo() {
  updating.value = true;
  try {
    const result = await api.updateAgentsRepo();
    emit('message', result.updated ? 'Repositorio actualizado' : 'Ya esta al dia', 'success');
    await loadRepoInfo();
  } catch (e) {
    emit('message', `Error actualizando: ${e}`, 'error');
  } finally {
    updating.value = false;
  }
}

async function removeRepo() {
  configStore.config.agents_repo_enabled = false;
  configStore.config.agents_repo_url = '';
  repoUrl.value = '';
  repoInfo.value = { exists: false };
  emit('message', 'Repositorio desvinculado. Se usara el agente por defecto.', 'success');
}

// --- Custom prompt ---
const generating = ref(false);

async function generateAgents() {
  if (!configStore.config.agents_custom_prompt.trim()) return;
  generating.value = true;
  try {
    await api.generateCustomAgents(configStore.config.agents_custom_prompt);
    emit('message', 'Agentes generados correctamente', 'success');
    await loadRepoInfo();
  } catch (e) {
    emit('message', `Error generando agentes: ${e}`, 'error');
  } finally {
    generating.value = false;
  }
}

onMounted(async () => {
  await checkCli();
  await loadRepoInfo();
});
</script>

<template>
  <div class="tab-content">
    <!-- Estado de Claude Code CLI -->
    <SettingGroup title="Claude Code CLI" description="Necesario para generar bloques de imputacion automaticamente.">
      <div class="cli-status">
        <div v-if="cliChecking" class="status-row">
          <Loader2 :size="16" class="spin" />
          <span>Comprobando...</span>
        </div>
        <template v-else>
          <div class="status-row" :class="cliInstalled ? 'ok' : 'fail'">
            <CheckCircle2 v-if="cliInstalled" :size="16" />
            <XCircle v-else :size="16" />
            <span>{{ cliInstalled ? `Instalado (${cliVersion || 'version desconocida'})` : 'No instalado' }}</span>
          </div>
          <div v-if="cliInstalled" class="status-row" :class="cliAuthenticated ? 'ok' : 'fail'">
            <CheckCircle2 v-if="cliAuthenticated" :size="16" />
            <XCircle v-else :size="16" />
            <span>{{ cliAuthenticated ? (cliAccount || 'Sesion activa') : 'No autenticado — ejecuta: claude auth login' }}</span>
          </div>
        </template>
        <button type="button" class="btn-check" @click="checkCli" :disabled="cliChecking" aria-label="Comprobar estado">
          <RefreshCw :size="14" :class="{ spin: cliChecking }" />
          Comprobar
        </button>
      </div>

      <!-- Fallback si no está disponible -->
      <div v-if="cliInstalled === false || cliAuthenticated === false" class="fallback-section">
        <div class="fallback-warning">
          <AlertTriangle :size="16" />
          <span>Sin Claude Code CLI la generacion de bloques no estara disponible.</span>
        </div>
        <SettingRow label="Alternativa" help="Que hacer cuando Claude Code CLI no esta disponible.">
          <CustomSelect v-model="configStore.config.generation_fallback" :options="[
            { value: 'disabled', label: 'Deshabilitar generacion' },
            { value: 'api', label: 'Usar proveedor IA (API)', hint: 'Requiere API key configurada' },
          ]" />
        </SettingRow>
      </div>
    </SettingGroup>

    <!-- Repositorio de agentes -->
    <SettingGroup
      v-if="cliInstalled && cliAuthenticated"
      title="Repositorio de agentes"
      description="Usa un repositorio con configuracion personalizada de agentes (CLAUDE.md, .claude/agents/, etc.)."
    >
      <div v-if="repoInfo?.exists && configStore.config.agents_repo_enabled" class="repo-card">
        <div class="repo-header">
          <FolderGit2 :size="18" />
          <div class="repo-meta">
            <span class="repo-url">{{ repoInfo.remote_url }}</span>
            <span class="repo-detail">
              {{ repoInfo.last_commit }}
              <template v-if="repoInfo.agent_count"> · {{ repoInfo.agent_count }} agente(s)</template>
              <template v-if="repoInfo.has_claude_md"> · CLAUDE.md</template>
              <template v-if="repoInfo.has_claude_dir"> · .claude/</template>
            </span>
          </div>
        </div>
        <div v-if="(repoInfo.agent_count ?? 0) > 3" class="repo-warning">
          <AlertTriangle :size="14" />
          <span>Muchos agentes pueden aumentar el tiempo de generacion de bloques.</span>
        </div>
        <div class="repo-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="updateRepo" :disabled="updating">
            <RefreshCw :size="12" :class="{ spin: updating }" />
            {{ updating ? 'Actualizando...' : 'Actualizar' }}
          </button>
          <button type="button" class="btn btn-danger btn-sm" @click="removeRepo" aria-label="Desvincular repositorio">
            <Trash2 :size="12" />
            Desvincular
          </button>
        </div>
      </div>

      <div v-else class="repo-setup">
        <SettingRow label="URL del repositorio" help="URL git del repositorio con la configuracion de agentes." :fullWidth="true">
          <div class="repo-input">
            <input type="url" v-model="repoUrl" placeholder="https://github.com/org/mimir-agents.git" />
            <button type="button" class="btn btn-secondary btn-sm" @click="cloneRepo" :disabled="cloning || !repoUrl.trim()">
              {{ cloning ? 'Clonando...' : 'Clonar' }}
            </button>
          </div>
        </SettingRow>
      </div>

      <!-- Auto-update -->
      <template v-if="repoInfo?.exists && configStore.config.agents_repo_enabled">
        <SettingRow label="Actualizacion automatica" help="Mantiene el repositorio de agentes actualizado con git pull.">
          <label class="toggle">
            <input type="checkbox" v-model="configStore.config.agents_auto_update" />
            <span class="toggle-label">{{ configStore.config.agents_auto_update ? 'Activo' : 'Desactivado' }}</span>
          </label>
        </SettingRow>
        <template v-if="configStore.config.agents_auto_update">
          <SettingRow label="Modo" help="Cuando actualizar el repositorio automaticamente.">
            <CustomSelect v-model="configStore.config.agents_update_mode" :options="[
              { value: 'startup_interval', label: 'Al arrancar + intervalo' },
              { value: 'fixed_time', label: 'A hora fija' },
            ]" />
          </SettingRow>
          <SettingRow v-if="configStore.config.agents_update_mode === 'startup_interval'" label="Intervalo" help="Cada cuantas horas comprobar actualizaciones.">
            <div class="inline-field">
              <input type="number" v-model.number="configStore.config.agents_update_interval_hours" min="1" max="168" />
              <span class="suffix">horas</span>
            </div>
          </SettingRow>
          <SettingRow v-if="configStore.config.agents_update_mode === 'fixed_time'" label="Hora" help="Hora del dia para comprobar actualizaciones.">
            <input type="time" v-model="configStore.config.agents_update_time" class="time-input" />
          </SettingRow>
        </template>
      </template>
    </SettingGroup>

    <!-- Prompt personalizado -->
    <SettingGroup
      v-if="cliInstalled && cliAuthenticated && !configStore.config.agents_repo_enabled"
      title="Personalizacion"
      description="Describe como quieres que se generen tus bloques y Claude creara la configuracion de agentes."
    >
      <SettingRow label="Prompt" help="Describe tus reglas de imputacion: proyectos, tipos de reunion, tareas recurrentes, etc." :fullWidth="true">
        <textarea
          v-model="configStore.config.agents_custom_prompt"
          rows="5"
          placeholder="Ej: Las reuniones daily van al proyecto Temas Internos. Los commits en ramas gextia_* van al proyecto Gextia..."
        ></textarea>
      </SettingRow>
      <button
        v-if="configStore.config.agents_custom_prompt.trim()"
        type="button"
        class="btn btn-secondary"
        @click="generateAgents"
        :disabled="generating"
      >
        <Loader2 v-if="generating" :size="14" class="spin" />
        {{ generating ? 'Generando agentes...' : 'Generar configuracion de agentes' }}
      </button>
    </SettingGroup>
  </div>
</template>

<style scoped>
@import '../../assets/settings-shared.css';

.tab-content { margin-bottom: 20px; }

/* CLI Status */
.cli-status {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.status-row.ok { color: var(--success); }
.status-row.fail { color: var(--error); }

.btn-check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast);
  align-self: flex-start;
  margin-top: var(--space-1);
}

.btn-check:hover { color: var(--text-primary); border-color: var(--text-secondary); }
.btn-check:disabled { opacity: 0.5; }

/* Fallback */
.fallback-section { margin-top: var(--space-3); }

.fallback-warning {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--warning-soft);
  border: 1px solid var(--warning);
  border-radius: var(--radius-md);
  color: var(--warning);
  font-size: var(--text-xs);
  margin-bottom: var(--space-3);
}

/* Repo card */
.repo-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
}

.repo-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  color: var(--text-primary);
}

.repo-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.repo-url {
  font-size: var(--text-sm);
  font-weight: 500;
  word-break: break-all;
}

.repo-detail {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.repo-warning {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--warning-soft);
  border-radius: var(--radius-sm);
  color: var(--warning);
  font-size: var(--text-xs);
}

.repo-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

/* Repo setup */
.repo-input {
  display: flex;
  gap: var(--space-2);
}

.repo-input input { flex: 1; }

/* Time input */
.time-input {
  width: 120px;
}

/* Spin */
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
