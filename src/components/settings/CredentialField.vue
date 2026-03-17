<script setup lang="ts">
import { ref } from 'vue';

withDefaults(defineProps<{
  label: string;
  stored: boolean;
  placeholder?: string;
  testable?: boolean;
}>(), {
  placeholder: '',
  testable: false,
});

const emit = defineEmits<{
  save: [value: string];
  delete: [];
  test: [];
}>();

const tokenValue = ref('');

function handleSave() {
  if (tokenValue.value) {
    emit('save', tokenValue.value);
    tokenValue.value = '';
  }
}
</script>

<template>
  <div class="credential-field">
    <template v-if="stored">
      <span class="credential-stored">&bull;&bull;&bull;&bull; (guardado)</span>
      <button v-if="testable" type="button" class="btn btn-secondary btn-sm" @click="emit('test')">Probar</button>
      <button type="button" class="btn btn-danger btn-sm" @click="emit('delete')">Eliminar</button>
    </template>
    <template v-else>
      <div class="token-field">
        <input
          type="password"
          v-model="tokenValue"
          :placeholder="placeholder || label"
          @keyup.enter="handleSave"
        />
        <button type="button" class="btn btn-secondary btn-sm" :disabled="!tokenValue" @click="handleSave">Guardar</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.credential-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.credential-stored {
  color: var(--text-secondary);
  font-size: 13px;
  margin-right: 4px;
}

.token-field {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.token-field input {
  flex: 1;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
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
.btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-hover); }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover:not(:disabled) { background: rgba(241, 76, 76, 0.1); }
.btn:disabled { opacity: 0.5; }
</style>
