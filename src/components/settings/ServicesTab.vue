<script setup lang="ts">
import { ref, computed } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import { api } from '../../lib/api';
import HelpTooltip from '../shared/HelpTooltip.vue';

const props = defineProps<{
  integrationStatus: Record<string, unknown>;
  googleCalendarConnected: boolean;
  authorizingGoogle: boolean;
}>();

const emit = defineEmits<{
  'message': [text: string, type: 'success' | 'error'];
  'authorize-google': [];
  'disconnect-google': [];
}>();

const configStore = useConfigStore();
const daemonStore = useDaemonStore();
const togglingCapture = ref(false);
const togglingServer = ref(false);

interface OdooStatus { configured: boolean; client_type: string | null; }

const odooIntegrationStatus = computed((): OdooStatus => {
  const odoo = props.integrationStatus?.odoo;
  if (odoo && typeof odoo === 'object') {
    const s = odoo as Record<string, unknown>;
    return { configured: Boolean(s.configured), client_type: (s.client_type as string) ?? null };
  }
  return { configured: false, client_type: null };
});

const gitlabIntegrationConfigured = computed((): boolean => {
  const gitlab = props.integrationStatus?.gitlab;
  return gitlab && typeof gitlab === 'object' ? Boolean((gitlab as Record<string, unknown>).configured) : false;
});

async function toggleCapture() {
  togglingCapture.value = true;
  try {
    if (daemonStore.captureConnected) {
      await api.stopCapture();
    } else {
      await api.startCapture();
    }
    await new Promise(r => setTimeout(r, 1000));
    await daemonStore.captureHealthCheck();
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  } finally {
    togglingCapture.value = false;
  }
}

async function toggleServer() {
  togglingServer.value = true;
  try {
    if (daemonStore.connected) {
      await api.stopServer();
    } else {
      await api.startServer();
    }
    await new Promise(r => setTimeout(r, 1500));
    await daemonStore.healthCheck();
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  } finally {
    togglingServer.value = false;
  }
}
</script>

<template>
  <div class="tab-content">
    <table class="service-status-table">
      <thead>
        <tr>
          <th>Servicio</th>
          <th>Estado</th>
          <th>Puerto</th>
          <th>Detalle</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="service-name">Captura de actividad <HelpTooltip text="Servicio systemd que captura la ventana activa, proyecto git y rama cada 30 segundos. Debe estar siempre activo." /></td>
          <td>
            <span class="badge" :class="daemonStore.captureConnected ? 'ok' : 'off'">
              {{ daemonStore.captureConnected ? 'Activo' : 'Inactivo' }}
            </span>
          </td>
          <td class="mono">9476</td>
          <td class="detail">Proceso systemd, siempre activo</td>
          <td class="action-cell">
            <button
              type="button"
              class="btn btn-sm"
              :class="daemonStore.captureConnected ? 'btn-danger' : 'btn-success'"
              :disabled="togglingCapture"
              @click="toggleCapture"
            >
              {{ togglingCapture ? '...' : (daemonStore.captureConnected ? 'Detener' : 'Iniciar') }}
            </button>
          </td>
        </tr>
        <tr>
          <td class="service-name">Servidor API <HelpTooltip text="Servidor que gestiona bloques, integraciones con Odoo/GitLab y descripciones IA. Se lanza automaticamente al abrir la app." /></td>
          <td>
            <span class="badge" :class="daemonStore.connected ? 'ok' : 'off'">
              {{ daemonStore.connected ? 'Activo' : 'Inactivo' }}
            </span>
          </td>
          <td class="mono">{{ configStore.config.daemon_port }}</td>
          <td class="detail">
            <template v-if="daemonStore.connected">
              <span class="mode-badge" :class="daemonStore.status.mode">{{ daemonStore.modeLabel }}</span>
              {{ daemonStore.status.blocks_today }} bloques hoy — Uptime {{ Math.floor(daemonStore.status.uptime_seconds / 60) }}min
            </template>
            <template v-else>Lanzado al abrir la app</template>
          </td>
          <td class="action-cell">
            <button
              type="button"
              class="btn btn-sm"
              :class="daemonStore.connected ? 'btn-danger' : 'btn-success'"
              :disabled="togglingServer"
              @click="toggleServer"
            >
              {{ togglingServer ? '...' : (daemonStore.connected ? 'Detener' : 'Iniciar') }}
            </button>
          </td>
        </tr>
        <tr>
          <td class="service-name">Odoo <HelpTooltip text="Integracion con Odoo para enviar partes de horas. Configurar en la pestaña Odoo." /></td>
          <td>
            <span class="badge" :class="odooIntegrationStatus.configured ? 'ok' : 'off'">
              {{ odooIntegrationStatus.configured ? 'Conectado' : 'No' }}
            </span>
          </td>
          <td class="mono">&mdash;</td>
          <td class="detail">
            <template v-if="odooIntegrationStatus.configured">
              {{ configStore.config.odoo_username || '—' }} — {{ odooIntegrationStatus.client_type }}
            </template>
            <template v-else>Configurar en pestaña Odoo</template>
          </td>
          <td></td>
        </tr>
        <tr>
          <td class="service-name">GitLab <HelpTooltip text="Integracion con GitLab para ver issues y merge requests asignadas. Configurar en la pestaña GitLab." /></td>
          <td>
            <span class="badge" :class="gitlabIntegrationConfigured ? 'ok' : 'off'">
              {{ gitlabIntegrationConfigured ? 'Conectado' : 'No' }}
            </span>
          </td>
          <td class="mono">&mdash;</td>
          <td class="detail">
            <template v-if="gitlabIntegrationConfigured">
              {{ configStore.config.gitlab_url.replace(/^https?:\/\//, '') }} — API v4
            </template>
            <template v-else>Configurar en pestaña GitLab</template>
          </td>
          <td></td>
        </tr>
        <tr>
          <td class="service-name">Inteligencia Artificial <HelpTooltip text="Genera descripciones automaticas de cada bloque de actividad usando IA. Configurar en la pestaña IA." /></td>
          <td>
            <span class="badge" :class="configStore.config.ai_provider !== 'none' ? (configStore.config.ai_api_key_stored ? 'ok' : 'warn') : 'off'">
              {{ configStore.config.ai_provider !== 'none' ? (configStore.config.ai_api_key_stored ? 'Activo' : 'Sin API key') : 'Desactivado' }}
            </span>
          </td>
          <td class="mono">&mdash;</td>
          <td class="detail">
            <template v-if="configStore.config.ai_provider !== 'none'">
              {{ configStore.config.ai_provider.charAt(0).toUpperCase() + configStore.config.ai_provider.slice(1) }}
              — Perfil {{ configStore.config.ai_user_role }}
            </template>
            <template v-else>Configurar en pestaña IA</template>
          </td>
          <td></td>
        </tr>
        <tr>
          <td class="service-name">Google Calendar <HelpTooltip text="Conecta con Google Calendar para detectar reuniones automaticamente y enriquecer los bloques con datos del evento." /></td>
          <td>
            <span class="badge" :class="googleCalendarConnected ? 'ok' : 'off'">
              {{ googleCalendarConnected ? 'Conectado' : 'No' }}
            </span>
          </td>
          <td class="mono">&mdash;</td>
          <td class="detail">
            <template v-if="googleCalendarConnected">Eventos del calendario enriquecen las señales</template>
            <template v-else-if="configStore.config.google_client_id">Autoriza el acceso a tu calendario</template>
            <template v-else>Configura Client ID y Secret en la pestaña Google</template>
          </td>
          <td class="action-cell">
            <button
              v-if="configStore.config.google_client_id && !googleCalendarConnected"
              type="button"
              class="btn btn-sm btn-success"
              :disabled="authorizingGoogle"
              @click="emit('authorize-google')"
            >
              {{ authorizingGoogle ? 'Abriendo...' : 'Autorizar' }}
            </button>
            <button
              v-else-if="googleCalendarConnected"
              type="button"
              class="btn btn-sm btn-danger"
              @click="emit('disconnect-google')"
            >
              Desconectar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}

/* Status table (services) */
.service-status-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.service-status-table th {
  text-align: left;
  padding: 10px 10px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 12px;
  border-bottom: 2px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.service-status-table td {
  padding: 10px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.service-status-table tr:hover td {
  background: var(--bg-hover);
}

.service-name {
  font-weight: 500;
  white-space: nowrap;
}

.mono {
  font-family: monospace;
  color: var(--text-secondary);
}

.detail {
  color: var(--text-secondary);
  font-size: 12px;
}

.action-cell { white-space: nowrap; }

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
}

.badge.ok { background: var(--success-soft); color: var(--success); }
.badge.off { background: rgba(162, 176, 180, 0.15); color: var(--text-secondary); }
.badge.warn { background: var(--warning-soft); color: var(--warning); }

.mode-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  margin-right: 4px;
}

.mode-badge.active { background: var(--success-soft); color: var(--success); }
.mode-badge.silent { background: var(--warning-soft); color: var(--warning); }
.mode-badge.paused { background: var(--error-soft); color: var(--error); }

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
.btn-success { background: var(--success); color: white; }
.btn-success:hover:not(:disabled) { opacity: 0.85; }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: var(--error-soft); }
.btn:disabled { opacity: 0.5; }
</style>
