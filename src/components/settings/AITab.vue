<script setup lang="ts">
import { ref } from 'vue';
import { useConfigStore } from '../../stores/config';
import CustomSelect from '../shared/CustomSelect.vue';
import SettingGroup from './SettingGroup.vue';
import SettingRow from './SettingRow.vue';

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
    <SettingGroup title="Proveedor IA">
      <SettingRow label="Proveedor" help="Servicio de IA para generar descripciones automaticas de los bloques de actividad.">
        <CustomSelect v-model="configStore.config.ai_provider" :options="[
          { value: 'none', label: 'Desactivado' },
          { value: 'gemini', label: 'Google Gemini', hint: 'gemini-2.0-flash' },
          { value: 'claude', label: 'Anthropic Claude', hint: 'claude-haiku' },
          { value: 'openai', label: 'OpenAI', hint: 'gpt-4o-mini' },
        ]" />
      </SettingRow>
      <template v-if="configStore.config.ai_provider !== 'none'">
        <SettingRow label="API Key" help="Clave de API del proveedor seleccionado. Se guarda de forma segura en el keyring.">
          <div class="token-field">
            <input type="password" v-model="aiToken" :placeholder="configStore.config.ai_api_key_stored ? '***** (guardada)' : 'API key'" />
            <button v-if="configStore.config.ai_api_key_stored" type="button" class="btn btn-danger btn-sm" @click="clearAIToken">Eliminar</button>
          </div>
        </SettingRow>
        <SettingRow label="Perfil" help="Tu rol profesional. La IA adapta el lenguaje de las descripciones segun este perfil.">
          <CustomSelect v-model="configStore.config.ai_user_role" :options="[
            { value: 'technical', label: 'Tecnico', hint: 'Desarrollo, ops' },
            { value: 'functional', label: 'Funcional', hint: 'Consultor, analista' },
            { value: 'other', label: 'Otro' },
          ]" />
        </SettingRow>
        <SettingRow label="Contexto" help="Informacion adicional sobre tu trabajo. Ayuda a la IA a generar descripciones mas precisas y relevantes." :fullWidth="true">
          <textarea v-model="configStore.config.ai_custom_context" rows="3" placeholder="Ej: Desarrollador backend, modulos account y sale"></textarea>
        </SettingRow>
      </template>
    </SettingGroup>
    <p v-if="configStore.config.ai_provider !== 'none'" class="hint">
      Las descripciones se generan automaticamente al cerrar cada bloque de actividad.
    </p>
  </div>
</template>

<style scoped>
.tab-content {
  margin-bottom: 20px;
}

.hint {
  font-size: 11px;
  color: var(--text-secondary);
  font-style: italic;
  margin-top: 8px;
  padding-left: 130px;
}
</style>
