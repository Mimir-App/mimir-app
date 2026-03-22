<script setup lang="ts">
import { ref, computed } from 'vue';
import { useConfigStore } from '../../stores/config';
import { useDaemonStore } from '../../stores/daemon';
import CustomSelect from '../shared/CustomSelect.vue';
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
const odooToken = ref('');
const odooUrl = ref('');
const odooVersion = ref('v16');
const odooDb = ref('');
const odooUsername = ref('');
const showOdooModal = ref(false);
const testingOdoo = ref(false);
const odooTestResult = ref<'ok' | 'fail' | null>(null);
const odooTestMessage = ref('');

interface OdooStatus { configured: boolean; client_type: string | null; }

const odooIntegrationStatus = computed((): OdooStatus => {
  const odoo = props.integrationStatus?.odoo;
  if (odoo && typeof odoo === 'object') {
    const s = odoo as Record<string, unknown>;
    return { configured: Boolean(s.configured), client_type: (s.client_type as string) ?? null };
  }
  return { configured: false, client_type: null };
});

async function clearOdooToken() {
  try {
    await configStore.deleteOdooToken();
    emit('message', 'Token Odoo eliminado', 'success');
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  }
}

function openOdooModal() {
  odooUrl.value = configStore.config.odoo_url;
  odooVersion.value = configStore.config.odoo_version;
  odooDb.value = configStore.config.odoo_db;
  odooUsername.value = configStore.config.odoo_username;
  odooToken.value = '';
  showOdooModal.value = true;
}

async function confirmOdooModal() {
  configStore.config.odoo_url = odooUrl.value;
  configStore.config.odoo_version = odooVersion.value as 'v11' | 'v16';
  configStore.config.odoo_db = odooDb.value;
  configStore.config.odoo_username = odooUsername.value;
  if (odooToken.value) {
    await configStore.setOdooToken(odooToken.value);
    odooToken.value = '';
  }
  await configStore.save(configStore.config);
  showOdooModal.value = false;
  emit('message', 'Configuracion Odoo guardada', 'success');
}

async function testOdooConnection() {
  testingOdoo.value = true; odooTestResult.value = null; odooTestMessage.value = '';
  try {
    if (odooToken.value) { await configStore.setOdooToken(odooToken.value); odooToken.value = ''; }
    await configStore.save(configStore.config);
    if (!daemonStore.connected) { odooTestResult.value = 'fail'; odooTestMessage.value = 'Servidor API no conectado'; return; }
    const result = await configStore.pushToDaemon();
    emit('refresh-status');
    if (result.status === 'ok' && odooIntegrationStatus.value.configured) {
      odooTestResult.value = 'ok'; odooTestMessage.value = 'Conectado a Odoo';
    } else { odooTestResult.value = 'fail'; odooTestMessage.value = result.message ?? 'No se pudo conectar'; }
  } catch (e) { odooTestResult.value = 'fail'; odooTestMessage.value = e instanceof Error ? e.message : String(e); }
  finally { testingOdoo.value = false; }
}
</script>

<template>
  <div class="tab-content">
    <IntegrationCard
      name="Odoo"
      description="Imputar horas, gestionar proyectos y fichar jornada."
      :connected="odooIntegrationStatus.configured"
      connect-label="Configurar Odoo"
      :testing="testingOdoo"
      :test-result="odooTestResult"
      :test-message="odooTestMessage"
      @connect="openOdooModal"
      @edit="openOdooModal"
      @test="testOdooConnection"
      @disconnect="clearOdooToken"
    >
      <template #icon>
        <img
          v-if="configStore.config.odoo_url"
          :src="configStore.config.odoo_url.replace(/\/$/, '') + '/web/image/res.company/1/logo'"
          :alt="'Odoo'"
          style="width: 24px; height: 24px; object-fit: contain;"
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        />
        <span v-else style="font-size: 18px; font-weight: 700; color: #714B67;">O</span>
      </template>
      <template #status>
        <p class="session-detail">{{ configStore.config.odoo_username }} — {{ configStore.config.odoo_url.replace(/^https?:\/\//, '') }}</p>
      </template>
      <template #details>
        <table class="settings-table">
          <tbody>
            <tr>
              <td class="label-cell">Servidor</td>
              <td>{{ configStore.config.odoo_url }}</td>
              <td class="label-cell">Version</td>
              <td>{{ configStore.config.odoo_version }}</td>
            </tr>
            <tr>
              <td class="label-cell">Usuario</td>
              <td>{{ configStore.config.odoo_username }}</td>
              <td class="label-cell">Base de datos</td>
              <td>{{ configStore.config.odoo_db }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </IntegrationCard>

    <ModalDialog title="Configurar Odoo" :open="showOdooModal" showFooter @close="showOdooModal = false" @confirm="confirmOdooModal">
      <table class="settings-table">
        <tbody>
          <tr>
            <td class="label-cell">URL</td>
            <td><input type="url" v-model="odooUrl" placeholder="https://odoo.example.com" /></td>
          </tr>
          <tr>
            <td class="label-cell">Version</td>
            <td>
              <CustomSelect v-model="odooVersion" :options="[
                { value: 'v11', label: 'Odoo v11', hint: 'XMLRPC' },
                { value: 'v16', label: 'Odoo v16+', hint: 'REST / OAuth' },
              ]" />
            </td>
          </tr>
          <tr>
            <td class="label-cell">Base de datos</td>
            <td><input type="text" v-model="odooDb" placeholder="nombre_base_datos" /></td>
          </tr>
          <tr>
            <td class="label-cell">Usuario</td>
            <td><input type="text" v-model="odooUsername" placeholder="usuario@empresa.com" /></td>
          </tr>
          <tr>
            <td class="label-cell">Token</td>
            <td>
              <div class="token-field">
                <input type="password" v-model="odooToken" :placeholder="configStore.config.odoo_token_stored ? '***** (guardado)' : 'Contrasena o API key'" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </ModalDialog>
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
