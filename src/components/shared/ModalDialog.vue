<script setup lang="ts">
defineProps<{
  title: string;
  open: boolean;
  showFooter?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <button class="modal-close" @click="emit('close')">&times;</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div v-if="showFooter || $slots.footer" class="modal-footer">
          <slot name="footer">
            <button type="button" class="btn btn-secondary" @click="emit('close')">Cancelar</button>
            <button type="button" class="btn btn-primary" @click="emit('confirm')">Aceptar</button>
          </slot>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-dialog { background: var(--bg-primary); border: 1px solid var(--border); border-radius: 12px; width: 90%; max-width: 520px; max-height: 80vh; display: flex; flex-direction: column; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-secondary); padding: 0 4px; }
.modal-close:hover { color: var(--text-primary); }
.modal-body { padding: 20px; overflow-y: auto; flex: 1; min-height: 0; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 20px; border-top: 1px solid var(--border); flex-shrink: 0; }
.btn { padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--bg-hover); }
</style>
