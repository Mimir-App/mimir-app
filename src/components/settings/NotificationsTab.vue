<script setup lang="ts">
import { useConfigStore } from '../../stores/config';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';

const configStore = useConfigStore();
</script>

<template>
  <div class="tab-content">
    <SettingGroup title="General">
      <SettingRow
        label="Notificaciones de escritorio"
        help="Activa o desactiva todas las notificaciones de la aplicacion."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_enabled" />
          <span class="toggle-label">{{ configStore.config.notification_enabled ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="Intervalo de comprobacion"
        help="Cada cuantos minutos se comprueban nuevas notificaciones en segundo plano."
      >
        <div class="inline-field">
          <input
            type="number"
            v-model.number="configStore.config.notification_interval_minutes"
            min="1"
            max="60"
          />
          <span class="suffix">min</span>
        </div>
      </SettingRow>

      <SettingRow
        label="Retencion"
        help="Dias que se conservan las notificaciones leidas antes de eliminarse automaticamente."
      >
        <div class="inline-field">
          <input
            type="number"
            v-model.number="configStore.config.notification_retention_days"
            min="1"
            max="90"
          />
          <span class="suffix">dias</span>
        </div>
      </SettingRow>
    </SettingGroup>

    <SettingGroup title="Tipos de notificacion">
      <SettingRow
        label="Nuevos comentarios"
        help="Notificar cuando hay nuevos comentarios en issues o MRs que sigues."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_comments" />
          <span class="toggle-label">{{ configStore.config.notification_comments ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="Pipeline fallido"
        help="Notificar cuando el pipeline de un MR tuyo falla."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_pipeline_failed" />
          <span class="toggle-label">{{ configStore.config.notification_pipeline_failed ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="MR aprobado"
        help="Notificar cuando uno de tus MRs recibe una aprobacion."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_mr_approved" />
          <span class="toggle-label">{{ configStore.config.notification_mr_approved ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="Cambios solicitados"
        help="Notificar cuando un revisor solicita cambios en un MR tuyo."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_changes_requested" />
          <span class="toggle-label">{{ configStore.config.notification_changes_requested ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="Conflictos detectados"
        help="Notificar cuando se detectan conflictos de merge en un MR que sigues."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_conflicts" />
          <span class="toggle-label">{{ configStore.config.notification_conflicts ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>

      <SettingRow
        label="Nuevos TODOs"
        help="Notificar cuando GitLab asigna nuevos TODOs a tu usuario."
      >
        <label class="toggle">
          <input type="checkbox" v-model="configStore.config.notification_todos" />
          <span class="toggle-label">{{ configStore.config.notification_todos ? 'Activo' : 'Desactivado' }}</span>
        </label>
      </SettingRow>
    </SettingGroup>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}
</style>
