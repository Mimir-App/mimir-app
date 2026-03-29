<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useConfigStore } from '../../stores/config';
import { api } from '../../lib/api';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';
import { Loader2 } from 'lucide-vue-next';

const configStore = useConfigStore();

// --- Navegadores detectados ---
const detectedBrowsers = ref<Array<{ name: string; path: string; icon?: string }>>([]);
const loadingBrowsers = ref(false);

const BROWSER_LABELS: Record<string, string> = {
  chrome: 'Google Chrome',
  chromium: 'Chromium',
  brave: 'Brave',
  vivaldi: 'Vivaldi',
  edge: 'Microsoft Edge',
  opera: 'Opera',
  firefox: 'Firefox',
};

const BROWSER_ICONS: Record<string, string> = {
  chrome: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#4285F4" stroke-width="1.5"/><circle cx="12" cy="12" r="4" fill="#4285F4"/><path d="M12 8h9.17" stroke="#EA4335" stroke-width="1.5"/><path d="M7.41 16.59L2.83 8" stroke="#FBBC05" stroke-width="1.5"/><path d="M16.59 16.59l-4.59 8" stroke="#34A853" stroke-width="1.5"/></svg>`,
  chromium: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#4587F3" stroke-width="1.5"/><circle cx="12" cy="12" r="4" fill="#4587F3"/><path d="M12 8h9.17" stroke="#4587F3" stroke-width="1.5"/><path d="M7.41 16.59L2.83 8" stroke="#4587F3" stroke-width="1.5"/><path d="M16.59 16.59l-4.59 8" stroke="#4587F3" stroke-width="1.5"/></svg>`,
  firefox: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#FF7139" stroke-width="1.5"/><path d="M12 6c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6" stroke="#FF7139" stroke-width="1.5"/><circle cx="12" cy="12" r="3" fill="#FF7139"/></svg>`,
  brave: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7L12 2z" stroke="#FB542B" stroke-width="1.5"/><path d="M12 8l3 2v4l-3 2-3-2v-4l3-2z" fill="#FB542B"/></svg>`,
  vivaldi: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#EF3939" stroke-width="1.5"/><circle cx="12" cy="12" r="5" stroke="#EF3939" stroke-width="1.5"/></svg>`,
  edge: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#0078D7" stroke-width="1.5"/><path d="M8 14c0-2.21 1.79-4 4-4s4 1.79 4 4" stroke="#0078D7" stroke-width="1.5"/><circle cx="12" cy="14" r="2" fill="#0078D7"/></svg>`,
  opera: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#FF1B2D" stroke-width="1.5"/><ellipse cx="12" cy="12" rx="4" ry="7" stroke="#FF1B2D" stroke-width="1.5"/></svg>`,
};

async function loadBrowsers() {
  loadingBrowsers.value = true;
  try {
    detectedBrowsers.value = await api.getDetectedBrowsers();
  } catch {
    detectedBrowsers.value = [];
  } finally {
    loadingBrowsers.value = false;
  }
}

function isBrowserSelected(name: string): boolean {
  const list = configStore.config.browser_history_browsers;
  // Lista vacía = todos seleccionados
  return !list || list.length === 0 || list.includes(name);
}

function toggleBrowser(name: string) {
  let list = [...(configStore.config.browser_history_browsers || [])];

  if (list.length === 0) {
    // Estaba en "todos" → seleccionar todos excepto este
    list = detectedBrowsers.value
      .map(b => b.name)
      .filter(n => n !== name);
  } else if (list.includes(name)) {
    list = list.filter(n => n !== name);
    // Si quedan todos seleccionados → volver a lista vacía
    if (list.length === detectedBrowsers.value.length) {
      list = [];
    }
  } else {
    list.push(name);
    if (list.length === detectedBrowsers.value.length) {
      list = [];
    }
  }

  configStore.config.browser_history_browsers = list;
}

onMounted(() => {
  if (configStore.config.capture_browser_history) {
    loadBrowsers();
  }
});

watch(() => configStore.config.capture_browser_history, (enabled) => {
  if (enabled && detectedBrowsers.value.length === 0) {
    loadBrowsers();
  }
});
</script>

<template>
  <div class="tab-content">
    <SettingGroup
      title="Permisos de captura"
      description="Controla que datos recopila el servicio de captura. Los cambios se aplican en el siguiente ciclo de polling."
    >
      <SettingRow label="Ventana activa" help="Captura la aplicacion y el titulo de la ventana activa cada 30 segundos. Es el dato principal para construir bloques.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_window" />
          <span class="toggle-label">{{ configStore.config.capture_window ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow label="Proyecto git" help="Detecta el repositorio git, rama y ultimo commit del proceso activo. Permite agrupar bloques por proyecto.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_git" />
          <span class="toggle-label">{{ configStore.config.capture_git ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow label="Tiempo inactivo" help="Detecta cuanto tiempo llevas sin tocar teclado o raton. Permite descontar tiempo AFK de los bloques.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_idle" />
          <span class="toggle-label">{{ configStore.config.capture_idle ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow label="Audio / reuniones" help="Detecta streams de audio activos para identificar videollamadas (Meet, Zoom, Teams, etc.) automaticamente.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_audio" />
          <span class="toggle-label">{{ configStore.config.capture_audio ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow label="Sesiones SSH" help="Detecta conexiones SSH activas para identificar trabajo en servidores remotos.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_ssh" />
          <span class="toggle-label">{{ configStore.config.capture_ssh ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow label="Historial del navegador" help="Lee el historial de Chrome, Firefox, Brave, etc. al generar bloques para enriquecer el contexto. Solo se lee bajo demanda, no se captura continuamente.">
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.capture_browser_history" />
          <span class="toggle-label">{{ configStore.config.capture_browser_history ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <!-- Navegadores detectados -->
      <div v-if="configStore.config.capture_browser_history" class="browser-list">
        <div v-if="loadingBrowsers" class="browser-loading">
          <Loader2 :size="14" class="spin" />
          <span>Detectando navegadores...</span>
        </div>
        <template v-else-if="detectedBrowsers.length > 0">
          <label
            v-for="browser in detectedBrowsers"
            :key="browser.name"
            class="browser-item"
          >
            <input
              type="checkbox"
              :checked="isBrowserSelected(browser.name)"
              @change="toggleBrowser(browser.name)"
            />
            <img v-if="browser.icon" :src="browser.icon" class="browser-icon" :alt="browser.name" />
            <span v-else class="browser-icon" v-html="BROWSER_ICONS[browser.name] || ''" />
            <span class="browser-name">{{ BROWSER_LABELS[browser.name] || browser.name }}</span>
            <span class="browser-path">{{ browser.path }}</span>
          </label>
        </template>
        <div v-else class="browser-empty">
          No se detectaron navegadores con historial accesible.
        </div>
      </div>
    </SettingGroup>

    <SettingGroup title="Retención">
      <SettingRow label="Umbral inactividad" help="Minutos sin actividad para cerrar un bloque automaticamente.">
        <div class="inline-field">
          <input type="number" v-model.number="configStore.config.inactivity_threshold_minutes" min="1" max="30" />
          <span class="suffix">min</span>
        </div>
      </SettingRow>

      <SettingRow label="Retención señales" help="Dias que se conservan las señales crudas. Pasado este tiempo se eliminan automaticamente para liberar espacio.">
        <div class="inline-field">
          <input type="number" v-model.number="configStore.config.signals_retention_days" min="30" max="730" />
          <span class="suffix">dias</span>
        </div>
      </SettingRow>

      <SettingRow label="Retención bloques" help="Dias que se conservan los bloques de actividad. Los bloques sincronizados con Odoo se pueden eliminar antes.">
        <div class="inline-field">
          <input type="number" v-model.number="configStore.config.blocks_retention_days" min="30" max="1825" />
          <span class="suffix">dias</span>
        </div>
      </SettingRow>
    </SettingGroup>
  </div>
</template>

<style scoped>
.tab-content { margin-bottom: 20px; }

/* Browser list */
.browser-list {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-main);
  border-radius: var(--radius-md);
  margin-left: var(--space-4);
}

.browser-loading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.browser-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--text-primary);
}

.browser-item input[type="checkbox"] {
  cursor: pointer;
}

img.browser-icon,
span.browser-icon {
  display: flex;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border-radius: 2px;
}
span.browser-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.browser-name {
  font-weight: 500;
}

.browser-path {
  font-size: var(--text-xs);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.browser-empty {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-style: italic;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
