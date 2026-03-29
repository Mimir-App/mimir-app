<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useConfigStore } from '../stores/config';
import { useDaemonStore } from '../stores/daemon';
import { api } from '../lib/api';
import CustomSelect from '../components/shared/CustomSelect.vue';
import SourceIcon from '../components/shared/SourceIcon.vue';
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Loader2,
  SkipForward,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
} from 'lucide-vue-next';

const router = useRouter();
const configStore = useConfigStore();
const daemonStore = useDaemonStore();

const currentStep = ref(0);

const steps = [
  { id: 'welcome', title: 'Bienvenido a Mimir', subtitle: 'Configuremos tu entorno de trabajo' },
  { id: 'odoo', title: 'Odoo', subtitle: 'Conecta tu instancia para imputar horas' },
  { id: 'repos', title: 'Repositorios', subtitle: 'Conecta GitLab y/o GitHub' },
  { id: 'google', title: 'Google Calendar', subtitle: 'Detecta reuniones automaticamente' },
  { id: 'capture', title: 'Captura', subtitle: 'Configura que datos recopila Mimir' },
  { id: 'agent', title: 'Claude Code CLI', subtitle: 'Generacion inteligente de bloques' },
  { id: 'sections', title: 'Secciones', subtitle: 'Elige que secciones quieres ver' },
  { id: 'done', title: 'Todo listo', subtitle: 'Tu configuracion esta lista' },
];

const stepId = computed(() => steps[currentStep.value].id);
const isFirst = computed(() => currentStep.value === 0);
const isLast = computed(() => currentStep.value === steps.length - 1);
const progress = computed(() => ((currentStep.value) / (steps.length - 1)) * 100);

function next() {
  if (!isLast.value) currentStep.value++;
}

function prev() {
  if (!isFirst.value) currentStep.value--;
}

async function finish() {
  await configStore.save({ ...configStore.config, onboarding_completed: true });
  if (daemonStore.connected) {
    await configStore.pushToDaemon();
  }
  router.push('/review');
}

// --- Odoo ---
const odooUrl = ref('');
const odooVersion = ref<'v11' | 'v16'>('v16');
const odooDb = ref('');
const odooUsername = ref('');
const odooToken = ref('');

function initOdoo() {
  odooUrl.value = configStore.config.odoo_url;
  odooVersion.value = configStore.config.odoo_version;
  odooDb.value = configStore.config.odoo_db;
  odooUsername.value = configStore.config.odoo_username;
  odooToken.value = '';
}

async function saveOdoo() {
  configStore.config.odoo_url = odooUrl.value;
  configStore.config.odoo_version = odooVersion.value;
  configStore.config.odoo_db = odooDb.value;
  configStore.config.odoo_username = odooUsername.value;
  if (odooToken.value) {
    await configStore.setOdooToken(odooToken.value);
    odooToken.value = '';
  }
  await configStore.save(configStore.config);
}

// --- GitLab ---
const gitlabUrl = ref('');
const gitlabToken = ref('');

function initRepos() {
  gitlabUrl.value = configStore.config.gitlab_url;
  gitlabToken.value = '';
  githubToken.value = '';
  githubAuthTab.value = 'oauth';
  oauthUserCode.value = '';
  oauthStatus.value = '';
  stopOAuthPolling();
}

async function saveGitlab() {
  configStore.config.gitlab_url = gitlabUrl.value;
  if (gitlabToken.value) {
    await configStore.setGitLabToken(gitlabToken.value);
    gitlabToken.value = '';
  }
  await configStore.save(configStore.config);
}

// --- GitHub ---
const githubToken = ref('');
const githubAuthTab = ref<'oauth' | 'pat'>('oauth');
const oauthLoading = ref(false);
const oauthUserCode = ref('');
const oauthVerificationUri = ref('');
const oauthDeviceCode = ref('');
const oauthPolling = ref(false);
const oauthStatus = ref('');
let oauthPollTimer: ReturnType<typeof setInterval> | null = null;

async function startOAuthFlow() {
  oauthLoading.value = true;
  oauthStatus.value = '';
  try {
    const result = await api.githubOAuthStart();
    if (result.error) { oauthStatus.value = `Error: ${result.error}`; return; }
    oauthUserCode.value = result.user_code;
    oauthVerificationUri.value = result.verification_uri;
    oauthDeviceCode.value = result.device_code;
    oauthStatus.value = 'waiting';
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_url', { url: result.verification_uri });
    } catch { /* usuario abrira manualmente */ }
    const interval = ((result.interval || 5) + 1) * 1000;
    oauthPolling.value = true;
    oauthPollTimer = setInterval(() => pollOAuth(), interval);
  } catch (e) { oauthStatus.value = `Error: ${e}`; }
  finally { oauthLoading.value = false; }
}

async function pollOAuth() {
  if (!oauthDeviceCode.value) return;
  try {
    const result = await api.githubOAuthPoll(oauthDeviceCode.value);
    if (result.status === 'complete' && result.access_token) {
      stopOAuthPolling();
      oauthStatus.value = 'complete';
      await configStore.setGitHubToken(result.access_token);
      await configStore.save(configStore.config);
    } else if (result.status === 'expired') {
      stopOAuthPolling();
      oauthStatus.value = 'El codigo ha expirado. Intentalo de nuevo.';
    } else if (result.status === 'error') {
      stopOAuthPolling();
      oauthStatus.value = `Error: ${result.error}`;
    } else if (result.status === 'slow_down') {
      stopOAuthPolling();
      const newInterval = (result.interval || 10) * 1000;
      oauthPolling.value = true;
      oauthPollTimer = setInterval(() => pollOAuth(), newInterval);
    }
  } catch { /* error de red, seguir intentando */ }
}

function stopOAuthPolling() {
  oauthPolling.value = false;
  if (oauthPollTimer) { clearInterval(oauthPollTimer); oauthPollTimer = null; }
}

async function saveGithubPAT() {
  if (githubToken.value) {
    await configStore.setGitHubToken(githubToken.value);
    githubToken.value = '';
    await configStore.save(configStore.config);
  }
}

// --- Google ---
const googleConnected = ref(false);
const authorizingGoogle = ref(false);

async function checkGoogleStatus() {
  try {
    const result = await api.getGoogleCalendarStatus() as { connected: boolean };
    googleConnected.value = result.connected;
  } catch { googleConnected.value = false; }
}

async function authorizeGoogle() {
  authorizingGoogle.value = true;
  try {
    const result = await api.getGoogleAuthUrl() as { url: string };
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('plugin:opener|open_url', { url: result.url });
    } catch { window.open(result.url, '_blank'); }
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      await checkGoogleStatus();
      if (googleConnected.value || attempts > 40) {
        clearInterval(interval);
        authorizingGoogle.value = false;
      }
    }, 3000);
  } catch { authorizingGoogle.value = false; }
}

// --- Agent / Claude CLI ---
const cliChecking = ref(false);
const cliInstalled = ref<boolean | null>(null);
const cliAuthenticated = ref<boolean | null>(null);
const cliVersion = ref<string | null>(null);
const agentRepoUrl = ref('');
const agentCloning = ref(false);
const agentChoice = ref<'repo' | 'custom' | 'default'>('default');

async function checkCli() {
  cliChecking.value = true;
  try {
    const result = await api.checkClaudeCli();
    cliInstalled.value = result.installed;
    cliAuthenticated.value = result.authenticated;
    cliVersion.value = result.version;
  } catch {
    cliInstalled.value = false;
    cliAuthenticated.value = false;
  } finally {
    cliChecking.value = false;
  }
}

async function cloneAgentRepo() {
  if (!agentRepoUrl.value.trim()) return;
  agentCloning.value = true;
  try {
    await api.cloneAgentsRepo(agentRepoUrl.value.trim());
    configStore.config.agents_repo_url = agentRepoUrl.value.trim();
    configStore.config.agents_repo_enabled = true;
    await configStore.save(configStore.config);
  } catch {
    // Error se maneja visualmente
  } finally {
    agentCloning.value = false;
  }
}

// --- Validación de conexión ---
const validating = ref(false);
const validationError = ref('');

async function validateConnection(): Promise<boolean> {
  validating.value = true;
  validationError.value = '';
  try {
    if (!daemonStore.connected) {
      validationError.value = 'Servidor API no conectado';
      return false;
    }

    // pushToDaemon devuelve el resultado con detalle de errores de auth
    const pushResult = await configStore.pushToDaemon();

    if (stepId.value === 'odoo') {
      // El daemon devuelve status "partial" + odoo "auth_failed" si credenciales incorrectas
      if (pushResult.status !== 'ok') {
        const msg = pushResult.message || 'No se pudo autenticar en Odoo';
        validationError.value = msg;
        return false;
      }
      // Doble check: verificar que el cliente quedó registrado
      const status = await configStore.getIntegrationStatus();
      const odoo = status?.odoo as Record<string, unknown> | undefined;
      if (!odoo?.configured) {
        validationError.value = 'No se pudo conectar a Odoo. Revisa las credenciales.';
        return false;
      }
      // Triple check: intentar obtener proyectos (verifica auth real)
      try {
        const projects = await api.getOdooProjects();
        if (!Array.isArray(projects)) {
          validationError.value = 'Credenciales de Odoo incorrectas.';
          return false;
        }
      } catch {
        validationError.value = 'No se pudo autenticar en Odoo. Revisa usuario y contrasena.';
        return false;
      }
    }

    if (stepId.value === 'repos') {
      const hasGitlab = gitlabUrl.value.trim() || configStore.config.gitlab_token_stored;
      const hasGithub = githubToken.value || configStore.config.github_token_stored;
      const status = await configStore.getIntegrationStatus();
      if (hasGitlab) {
        const gitlab = status?.gitlab as Record<string, unknown> | undefined;
        if (!gitlab?.configured) { validationError.value = 'No se pudo conectar a GitLab. Revisa URL y token.'; return false; }
      }
      if (hasGithub) {
        const github = status?.github as Record<string, unknown> | undefined;
        if (!github?.configured) { validationError.value = 'No se pudo conectar a GitHub. Revisa el token.'; return false; }
      }
      if (!hasGitlab && !hasGithub) return true;
    }

    if (stepId.value === 'google') {
      if (!googleConnected.value) { validationError.value = 'Google Calendar no conectado. Completa la autorizacion o pulsa Omitir.'; return false; }
    }

    return true;
  } catch (e) {
    validationError.value = `Error de validacion: ${e}`;
    return false;
  } finally {
    validating.value = false;
  }
}

// Pasos que requieren validación de conexión
const connectionSteps = ['odoo', 'repos', 'google'];

// --- Step change handler ---
async function handleNext() {
  validationError.value = '';

  // En pasos de conexión: Siguiente siempre exige datos + validación.
  // Para saltar sin datos, el usuario debe pulsar Omitir.
  if (connectionSteps.includes(stepId.value)) {
    // Verificar que hay datos mínimos
    if (stepId.value === 'odoo') {
      if (!odooUrl.value.trim()) { validationError.value = 'Introduce la URL de Odoo o pulsa Omitir para saltar este paso.'; return; }
      if (!odooUsername.value.trim()) { validationError.value = 'Introduce el usuario de Odoo.'; return; }
      if (!odooToken.value && !configStore.config.odoo_token_stored) { validationError.value = 'Introduce la contrasena o API key de Odoo.'; return; }
      if (!odooDb.value.trim()) { validationError.value = 'Introduce el nombre de la base de datos.'; return; }
    }
    if (stepId.value === 'repos' && !gitlabUrl.value.trim() && !gitlabToken.value && !configStore.config.gitlab_token_stored && !githubToken.value && !configStore.config.github_token_stored) {
      validationError.value = 'Configura al menos un repositorio o pulsa Omitir para saltar este paso.';
      return;
    }
    if (stepId.value === 'google' && !googleConnected.value) {
      validationError.value = 'Conecta Google Calendar o pulsa Omitir para saltar este paso.';
      return;
    }

    // Guardar datos antes de validar
    if (stepId.value === 'odoo') await saveOdoo();
    if (stepId.value === 'repos') { await saveGitlab(); await saveGithubPAT(); }

    // Validar conexión real
    const ok = await validateConnection();
    if (!ok) return;
  }

  next();
}

// Init data when entering steps
function onStepEnter() {
  if (stepId.value === 'odoo') initOdoo();
  if (stepId.value === 'repos') initRepos();
  if (stepId.value === 'google' && daemonStore.connected) checkGoogleStatus();
  if (stepId.value === 'agent') checkCli();
}

import { watch } from 'vue';
watch(currentStep, () => {
  validationError.value = '';
  onStepEnter();
});

onMounted(async () => {
  await configStore.load();
  onStepEnter();
});

onUnmounted(() => {
  stopOAuthPolling();
});
</script>

<template>
  <div class="onboarding">
    <!-- Progress bar -->
    <div class="progress-track" aria-hidden="true">
      <div class="progress-fill" :style="{ width: progress + '%' }"></div>
    </div>

    <!-- Step indicators -->
    <div class="step-dots">
      <button
        v-for="(step, i) in steps" :key="step.id"
        class="step-dot" :class="{ active: i === currentStep, done: i < currentStep }"
        :aria-label="step.title"
        @click="i < currentStep ? currentStep = i : undefined"
      >
        <Check v-if="i < currentStep" :size="12" :stroke-width="3" />
        <span v-else>{{ i + 1 }}</span>
      </button>
    </div>

    <!-- Content area -->
    <div class="step-content">
      <!-- Step: Welcome -->
      <div v-if="stepId === 'welcome'" class="step welcome-step">
        <img src="../assets/mimir-silhouette.svg" alt="Mimir" class="welcome-logo" />
        <h1>Mimir</h1>
        <p class="welcome-tagline">Asistente inteligente de imputacion de horas</p>
        <p class="welcome-description">
          Mimir captura tu actividad, detecta en que proyectos trabajas y genera automaticamente tus partes de horas para Odoo.
        </p>
        <div class="welcome-features">
          <div class="feature-item">
            <span class="feature-icon">1</span>
            <span>Captura automatica de actividad</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">2</span>
            <span>Integracion con GitLab, GitHub y Calendar</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">3</span>
            <span>Generacion inteligente de bloques</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">4</span>
            <span>Sincronizacion directa con Odoo</span>
          </div>
        </div>
      </div>

      <!-- Step: Odoo -->
      <div v-if="stepId === 'odoo'" class="step form-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>
        <div class="form-grid">
          <div class="form-field">
            <label>URL del servidor</label>
            <input type="url" v-model="odooUrl" placeholder="https://odoo.ejemplo.com" />
          </div>
          <div class="form-field">
            <label>Version</label>
            <CustomSelect v-model="odooVersion" :options="[
              { value: 'v11', label: 'Odoo v11', hint: 'XMLRPC' },
              { value: 'v16', label: 'Odoo v16+', hint: 'REST / API key' },
            ]" />
          </div>
          <div class="form-field">
            <label>Base de datos</label>
            <input type="text" v-model="odooDb" placeholder="nombre_base_datos" />
          </div>
          <div class="form-field">
            <label>Usuario</label>
            <input type="text" v-model="odooUsername" placeholder="usuario@empresa.com" />
          </div>
          <div class="form-field full">
            <label>Contrasena / API key</label>
            <input type="password" v-model="odooToken" :placeholder="configStore.config.odoo_token_stored ? '***** (guardado)' : 'Contrasena o API key'" />
          </div>
        </div>
      </div>

      <!-- Step: Repos -->
      <div v-if="stepId === 'repos'" class="step form-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>

        <!-- GitLab -->
        <div class="integration-block">
          <div class="integration-header">
            <SourceIcon source="gitlab" :size="20" />
            <span class="integration-name">GitLab</span>
          </div>
          <div class="form-grid">
            <div class="form-field">
              <label>URL</label>
              <input type="url" v-model="gitlabUrl" placeholder="https://gitlab.ejemplo.com" />
            </div>
            <div class="form-field">
              <label>Personal Access Token</label>
              <input type="password" v-model="gitlabToken" :placeholder="configStore.config.gitlab_token_stored ? '***** (guardado)' : 'Token'" />
            </div>
          </div>
        </div>

        <!-- GitHub -->
        <div class="integration-block">
          <div class="integration-header">
            <SourceIcon source="github" :size="20" />
            <span class="integration-name">GitHub</span>
          </div>
          <div class="github-auth-tabs">
            <button class="auth-tab" :class="{ active: githubAuthTab === 'oauth' }" @click="githubAuthTab = 'oauth'; stopOAuthPolling()">OAuth</button>
            <button class="auth-tab" :class="{ active: githubAuthTab === 'pat' }" @click="githubAuthTab = 'pat'; stopOAuthPolling()">Token manual</button>
          </div>
          <div v-if="githubAuthTab === 'oauth'" class="oauth-flow">
            <template v-if="!oauthUserCode">
              <p class="oauth-description">Autoriza Mimir en tu cuenta de GitHub.</p>
              <button class="btn-oauth" @click="startOAuthFlow" :disabled="oauthLoading || !daemonStore.connected">
                <SourceIcon source="github" :size="16" />
                {{ oauthLoading ? 'Conectando...' : 'Conectar con GitHub' }}
              </button>
              <p v-if="!daemonStore.connected" class="hint-error">Servidor API no conectado</p>
              <p v-if="oauthStatus && oauthStatus !== 'waiting'" class="hint-error">{{ oauthStatus }}</p>
            </template>
            <template v-else>
              <div class="oauth-code-box">
                <p class="oauth-instruction">Introduce este codigo en GitHub:</p>
                <div class="oauth-code">{{ oauthUserCode }}</div>
                <p class="oauth-url"><a :href="oauthVerificationUri" target="_blank" rel="noopener">{{ oauthVerificationUri }}</a></p>
              </div>
              <div v-if="oauthPolling" class="oauth-waiting">
                <Loader2 :size="16" class="spin" />
                Esperando autorizacion...
              </div>
              <p v-if="oauthStatus === 'complete'" class="hint-success">Conectado correctamente</p>
            </template>
          </div>
          <div v-if="githubAuthTab === 'pat'" class="form-grid">
            <div class="form-field full">
              <label>Personal Access Token</label>
              <input type="password" v-model="githubToken" :placeholder="configStore.config.github_token_stored ? '***** (guardado)' : 'Token (classic o fine-grained)'" />
              <span class="field-hint">Permisos: repo, read:org, notifications</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step: Google -->
      <div v-if="stepId === 'google'" class="step form-step center-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>
        <div v-if="googleConnected" class="status-card success">
          <Check :size="24" />
          <span>Google Calendar conectado</span>
        </div>
        <div v-else class="google-auth">
          <button class="btn-oauth" @click="authorizeGoogle" :disabled="authorizingGoogle || !daemonStore.connected">
            <span class="google-g">G</span>
            {{ authorizingGoogle ? 'Esperando autorizacion...' : 'Iniciar sesion con Google' }}
          </button>
          <p v-if="authorizingGoogle" class="hint-muted">
            <Loader2 :size="14" class="spin" />
            Completa la autorizacion en el navegador...
          </p>
          <p v-if="!daemonStore.connected" class="hint-error">Servidor API no conectado</p>
        </div>
      </div>

      <!-- Step: Capture -->
      <div v-if="stepId === 'capture'" class="step form-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>
        <div class="toggle-list">
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Ventana activa</span>
              <span class="toggle-hint">Captura la aplicacion y titulo de la ventana activa</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_window" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Proyecto git</span>
              <span class="toggle-hint">Detecta repositorio, rama y ultimo commit</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_git" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Tiempo inactivo</span>
              <span class="toggle-hint">Detecta inactividad de teclado y raton</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_idle" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Audio / reuniones</span>
              <span class="toggle-hint">Detecta videollamadas activas (Meet, Zoom, Teams)</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_audio" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Sesiones SSH</span>
              <span class="toggle-hint">Detecta conexiones SSH activas</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_ssh" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Historial del navegador</span>
              <span class="toggle-hint">Lee el historial al generar bloques (Chrome, Firefox, etc.)</span>
            </div>
            <input type="checkbox" v-model="configStore.config.capture_browser_history" />
          </label>
        </div>
      </div>

      <!-- Step: Agent -->
      <div v-if="stepId === 'agent'" class="step form-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>

        <!-- CLI status -->
        <div class="agent-status">
          <div v-if="cliChecking" class="status-row checking">
            <Loader2 :size="16" class="spin" />
            <span>Comprobando Claude Code CLI...</span>
          </div>
          <template v-else>
            <div class="status-row" :class="cliInstalled ? 'ok' : 'fail'">
              <CheckCircle2 v-if="cliInstalled" :size="16" />
              <XCircle v-else :size="16" />
              <span>{{ cliInstalled ? `Instalado (${cliVersion || '?'})` : 'No instalado' }}</span>
            </div>
            <div v-if="cliInstalled" class="status-row" :class="cliAuthenticated ? 'ok' : 'fail'">
              <CheckCircle2 v-if="cliAuthenticated" :size="16" />
              <XCircle v-else :size="16" />
              <span>{{ cliAuthenticated ? 'Sesion activa' : 'No autenticado — ejecuta: claude auth login' }}</span>
            </div>
            <button type="button" class="btn-recheck" @click="checkCli">
              <RefreshCw :size="12" />
              Volver a comprobar
            </button>
          </template>
        </div>

        <!-- Si no está disponible: fallback -->
        <div v-if="cliInstalled === false || cliAuthenticated === false" class="agent-fallback">
          <div class="fallback-banner">
            <AlertTriangle :size="16" />
            <span>Sin Claude Code CLI la generacion de bloques no estara disponible.</span>
          </div>
          <div class="choice-cards">
            <label class="choice-card" :class="{ selected: configStore.config.generation_fallback === 'disabled' }">
              <input type="radio" v-model="configStore.config.generation_fallback" value="disabled" />
              <span class="choice-title">Deshabilitar generacion</span>
              <span class="choice-desc">Crearas los bloques manualmente</span>
            </label>
            <label class="choice-card" :class="{ selected: configStore.config.generation_fallback === 'api' }">
              <input type="radio" v-model="configStore.config.generation_fallback" value="api" />
              <span class="choice-title">Usar proveedor IA (API)</span>
              <span class="choice-desc">Requiere API key (configurable en IA)</span>
            </label>
          </div>
        </div>

        <!-- Si está disponible: opciones de agentes -->
        <div v-if="cliInstalled && cliAuthenticated" class="agent-options">
          <p class="step-note">¿Tienes un repositorio con configuracion de agentes personalizada?</p>
          <div class="choice-cards">
            <label class="choice-card" :class="{ selected: agentChoice === 'repo' }">
              <input type="radio" v-model="agentChoice" value="repo" />
              <span class="choice-title">Tengo un repositorio</span>
              <span class="choice-desc">Clonare un repo con CLAUDE.md, agentes, etc.</span>
            </label>
            <label class="choice-card" :class="{ selected: agentChoice === 'custom' }">
              <input type="radio" v-model="agentChoice" value="custom" />
              <span class="choice-title">Quiero personalizar</span>
              <span class="choice-desc">Describire mis reglas y Claude creara la configuracion</span>
            </label>
            <label class="choice-card" :class="{ selected: agentChoice === 'default' }">
              <input type="radio" v-model="agentChoice" value="default" />
              <span class="choice-title">Usar configuracion por defecto</span>
              <span class="choice-desc">Funciona bien para la mayoria de casos</span>
            </label>
          </div>

          <!-- Repo URL -->
          <div v-if="agentChoice === 'repo'" class="agent-repo-form">
            <p class="step-note">Si el repositorio es privado, asegurate de tener acceso git configurado (SSH key o token).</p>
            <div class="form-field full">
              <label>URL del repositorio</label>
              <div class="repo-input">
                <input type="url" v-model="agentRepoUrl" placeholder="https://github.com/org/mimir-agents.git" />
                <button type="button" class="btn-clone" @click="cloneAgentRepo" :disabled="agentCloning || !agentRepoUrl.trim()">
                  {{ agentCloning ? 'Clonando...' : 'Clonar' }}
                </button>
              </div>
            </div>
            <div v-if="configStore.config.agents_repo_enabled" class="clone-success">
              <CheckCircle2 :size="16" />
              <span>Repositorio clonado correctamente</span>
            </div>
          </div>

          <!-- Custom prompt -->
          <div v-if="agentChoice === 'custom'" class="agent-custom-form">
            <div class="form-field full">
              <label>Describe tus reglas de imputacion</label>
              <textarea
                v-model="configStore.config.agents_custom_prompt"
                rows="4"
                placeholder="Ej: Las reuniones daily van al proyecto Temas Internos. Los commits en ramas gextia_* van al proyecto Gextia..."
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <!-- Step: Sections -->
      <div v-if="stepId === 'sections'" class="step form-step">
        <h2>{{ steps[currentStep].title }}</h2>
        <p class="step-subtitle">{{ steps[currentStep].subtitle }}</p>
        <p class="step-note">Revisar Dia y Ajustes estan siempre visibles. Puedes cambiar esto despues en Ajustes.</p>
        <div class="toggle-list">
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Dashboard</span>
              <span class="toggle-hint">Panel con widgets de resumen</span>
            </div>
            <input type="checkbox" v-model="configStore.config.section_dashboard" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Tareas</span>
              <span class="toggle-hint">Issues de GitLab y GitHub</span>
            </div>
            <input type="checkbox" v-model="configStore.config.section_issues" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Ramas</span>
              <span class="toggle-hint">Merge requests y pull requests</span>
            </div>
            <input type="checkbox" v-model="configStore.config.section_merge_requests" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Descubrir</span>
              <span class="toggle-hint">Busqueda universal en todos los repositorios</span>
            </div>
            <input type="checkbox" v-model="configStore.config.section_discover" />
          </label>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-name">Parte de horas</span>
              <span class="toggle-hint">Timesheets enviados a Odoo</span>
            </div>
            <input type="checkbox" v-model="configStore.config.section_timesheets" />
          </label>
        </div>
      </div>

      <!-- Step: Done -->
      <div v-if="stepId === 'done'" class="step welcome-step">
        <div class="done-icon">
          <Check :size="48" :stroke-width="2" />
        </div>
        <h1>Todo listo</h1>
        <p class="welcome-description">
          Tu configuracion esta completa. Puedes modificarla en cualquier momento desde Ajustes.
        </p>
      </div>
    </div>

    <!-- Validation error -->
    <div v-if="validationError" class="validation-bar" role="alert">
      <AlertTriangle :size="14" />
      <span>{{ validationError }}</span>
    </div>

    <!-- Navigation -->
    <div class="step-nav">
      <button v-if="!isFirst" class="btn-nav btn-back" @click="prev" :disabled="validating" aria-label="Paso anterior">
        <ChevronLeft :size="16" />
        Anterior
      </button>
      <div v-else></div>

      <div class="nav-right">
        <button v-if="!isFirst && !isLast" class="btn-nav btn-skip" @click="validationError = ''; next()" aria-label="Omitir paso">
          <SkipForward :size="14" />
          Omitir
        </button>
        <button v-if="!isLast" class="btn-nav btn-next" @click="isFirst ? next() : handleNext()" :disabled="validating" aria-label="Siguiente paso">
          <Loader2 v-if="validating" :size="14" class="spin" />
          {{ validating ? 'Verificando...' : 'Siguiente' }}
          <ChevronRight v-if="!validating" :size="16" />
        </button>
        <button v-if="isLast" class="btn-nav btn-finish" @click="finish" aria-label="Comenzar a usar Mimir">
          Comenzar
          <ChevronRight :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '../assets/settings-shared.css';

.onboarding {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Progress */
.progress-track {
  height: 3px;
  background: var(--border);
  flex-shrink: 0;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width var(--duration-slow) var(--ease-out);
}

/* Step dots */
.step-dots {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-5) 0 var(--space-2);
  flex-shrink: 0;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: none;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: 600;
  cursor: default;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-base) var(--ease-out);
}

.step-dot.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.step-dot.done {
  border-color: var(--success);
  background: var(--success);
  color: white;
  cursor: pointer;
}

/* Content */
.step-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  padding: var(--space-4) var(--space-6);
}

.step {
  width: 100%;
  max-width: 560px;
}

/* Welcome / Done */
.welcome-step {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding-top: var(--space-6);
}

.welcome-logo {
  width: 72px;
  height: 72px;
  margin-bottom: var(--space-2);
}

.welcome-step h1 {
  font-size: var(--text-3xl);
  font-weight: 700;
  background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-tagline {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  font-weight: 400;
}

.welcome-description {
  font-size: var(--text-sm);
  color: var(--text-muted);
  max-width: 400px;
  line-height: 1.6;
}

.welcome-features {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-5);
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.feature-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: var(--text-xs);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.done-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--success-soft);
  color: var(--success);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-2);
}

/* Form steps */
.form-step h2 {
  font-size: var(--text-xl);
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.step-subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-5);
}

.step-note {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: var(--space-4);
  font-style: italic;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-field.full {
  grid-column: 1 / -1;
}

.form-field label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.form-field input {
  width: 100%;
}

.field-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Integration blocks */
.integration-block {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.integration-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.integration-name {
  font-size: var(--text-base);
  font-weight: 600;
}

/* GitHub auth tabs */
.github-auth-tabs {
  display: flex;
  gap: 0;
  margin-bottom: var(--space-4);
  border-bottom: 2px solid var(--border);
}

.auth-tab {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.auth-tab:hover { color: var(--text-primary); }
.auth-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* OAuth flow */
.oauth-flow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}

.oauth-description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  text-align: center;
}

.btn-oauth {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-lg);
  background: var(--text-primary);
  color: var(--bg-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-oauth:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-oauth:disabled { opacity: 0.4; cursor: not-allowed; }

.google-g {
  font-size: 18px;
  font-weight: 700;
  color: var(--bg-primary);
}

.oauth-code-box {
  text-align: center;
  padding: var(--space-4);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  width: 100%;
}

.oauth-instruction { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2); }
.oauth-code { font-size: 28px; font-weight: 700; font-family: var(--font-mono); letter-spacing: 0.15em; color: var(--accent); padding: var(--space-2) 0; user-select: all; }
.oauth-url { font-size: var(--text-xs); margin-top: var(--space-2); }
.oauth-url a { color: var(--accent); text-decoration: none; }
.oauth-url a:hover { text-decoration: underline; }

.oauth-waiting {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* Status */
.status-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: 500;
}

.status-card.success {
  background: var(--success-soft);
  color: var(--success);
  border: 1px solid var(--success);
}

.center-step {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Toggle list */
.toggle-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.toggle-row:hover {
  background: var(--bg-hover);
}

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.toggle-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.toggle-row input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
  flex-shrink: 0;
}

/* Hints */
.hint-error { font-size: var(--text-xs); color: var(--error); text-align: center; }
.hint-success { font-size: var(--text-xs); color: var(--success); text-align: center; }
.hint-muted { font-size: var(--text-xs); color: var(--text-muted); display: flex; align-items: center; gap: var(--space-1); }

/* Spin animation */
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Navigation */
.step-nav {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.btn-nav {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-back {
  background: none;
  color: var(--text-secondary);
}

.btn-back:hover { color: var(--text-primary); }

.btn-skip {
  background: none;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.btn-skip:hover { color: var(--text-secondary); }

.btn-next, .btn-finish {
  background: var(--accent);
  color: white;
  padding: var(--space-2) var(--space-5);
}

.btn-next:hover, .btn-finish:hover { background: var(--accent-hover); }

/* Agent step */
.agent-status {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
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
.status-row.checking { color: var(--text-muted); }

.btn-recheck {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: var(--text-xs);
  cursor: pointer;
  padding: var(--space-1) 0;
  margin-top: var(--space-1);
}

.btn-recheck:hover { color: var(--text-primary); }

.fallback-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--warning-soft);
  border: 1px solid var(--warning);
  border-radius: var(--radius-md);
  color: var(--warning);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.choice-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.choice-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.choice-card:hover { background: var(--bg-hover); }

.choice-card.selected {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.choice-card input[type="radio"] { display: none; }

.choice-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.choice-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.agent-repo-form, .agent-custom-form {
  margin-top: var(--space-4);
}

.repo-input {
  display: flex;
  gap: var(--space-2);
}

.repo-input input { flex: 1; }

.btn-clone {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--accent);
  color: white;
  font-size: var(--text-sm);
  font-weight: 500;
  border: none;
  cursor: pointer;
  white-space: nowrap;
}

.btn-clone:hover:not(:disabled) { background: var(--accent-hover); }
.btn-clone:disabled { opacity: 0.5; }

.clone-success {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  color: var(--success);
  font-size: var(--text-sm);
}

.agent-options { margin-top: var(--space-2); }

/* Validation bar */
.validation-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-6);
  background: var(--error-soft);
  border-top: 1px solid var(--error);
  color: var(--error);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
  .progress-fill { transition: none; }
}
</style>
