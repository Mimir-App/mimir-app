<script setup lang="ts">
import { ref } from 'vue';
import { useConfigStore } from '../../stores/config';
import CustomSelect from '../shared/CustomSelect.vue';
import HelpTooltip from '../shared/HelpTooltip.vue';

const emit = defineEmits<{
  'message': [text: string, type: 'success' | 'error'];
}>();

const configStore = useConfigStore();
const aiToken = ref('');

async function clearAIToken() {
  try {
    await configStore.deleteAIToken();
    emit('message', 'API key IA eliminada', 'success');
  } catch (e) {
    emit('message', `Error: ${e}`, 'error');
  }
}
</script>

<template>
  <div class="tab-content">
    <table class="settings-table">
      <tbody>
        <tr>
          <td class="label-cell">Proveedor <HelpTooltip text="Servicio de IA para generar descripciones automaticas de los bloques de actividad." /></td>
          <td colspan="3">
            <CustomSelect v-model="configStore.config.ai_provider" :options="[
              { value: 'none', label: 'Desactivado' },
              { value: 'gemini', label: 'Google Gemini', hint: 'gemini-2.0-flash' },
              { value: 'claude', label: 'Anthropic Claude', hint: 'claude-haiku' },
              { value: 'openai', label: 'OpenAI', hint: 'gpt-4o-mini' },
            ]" />
          </td>
        </tr>
        <template v-if="configStore.config.ai_provider !== 'none'">
          <tr>
            <td class="label-cell">API Key <HelpTooltip text="Clave de API del proveedor seleccionado. Se guarda de forma segura en el keyring." /></td>
            <td colspan="3">
              <div class="token-field">
                <input type="password" v-model="aiToken" :placeholder="configStore.config.ai_api_key_stored ? '***** (guardada)' : 'API key'" />
                <button v-if="configStore.config.ai_api_key_stored" type="button" class="btn btn-danger btn-sm" @click="clearAIToken">Eliminar</button>
              </div>
            </td>
          </tr>
          <tr>
            <td class="label-cell">Perfil <HelpTooltip text="Tu rol profesional. La IA adapta el lenguaje de las descripciones segun este perfil." /></td>
            <td>
              <CustomSelect v-model="configStore.config.ai_user_role" :options="[
                { value: 'technical', label: 'Tecnico', hint: 'Desarrollo, ops' },
                { value: 'functional', label: 'Funcional', hint: 'Consultor, analista' },
                { value: 'other', label: 'Otro' },
              ]" />
            </td>
            <td class="label-cell"></td>
            <td></td>
          </tr>
          <tr>
            <td class="label-cell">Contexto <HelpTooltip text="Informacion adicional sobre tu trabajo. Ayuda a la IA a generar descripciones mas precisas y relevantes." /></td>
            <td colspan="3">
              <textarea v-model="configStore.config.ai_custom_context" rows="3" placeholder="Ej: Desarrollador backend, modulos account y sale"></textarea>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <p v-if="configStore.config.ai_provider !== 'none'" class="hint">
      Las descripciones se generan automaticamente al cerrar cada bloque de actividad.
    </p>
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
.settings-table select,
.settings-table textarea {
  width: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.settings-table textarea {
  resize: vertical;
}

.token-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.token-field input {
  flex: 1;
}

.hint {
  font-size: 11px;
  color: var(--text-secondary);
  font-style: italic;
  margin-top: 8px;
  padding-left: 130px;
}

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
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: rgba(241, 76, 76, 0.1); }
.btn:disabled { opacity: 0.5; }
</style>
