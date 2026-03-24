<script setup lang="ts">
import { useConfigStore } from '../../stores/config';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';

const configStore = useConfigStore();
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
</style>
