<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue';
import { X } from 'lucide-vue-next';

const props = defineProps<{
  title: string;
  open: boolean;
  showFooter?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();

const dialogRef = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close');
    return;
  }
  if (e.key === 'Tab' && dialogRef.value) {
    const focusable = dialogRef.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    previousFocus = document.activeElement as HTMLElement;
    await nextTick();
    dialogRef.value?.focus();
    document.addEventListener('keydown', handleKeydown);
  } else {
    document.removeEventListener('keydown', handleKeydown);
    previousFocus?.focus();
    previousFocus = null;
  }
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-overlay"
        role="presentation"
        @click.self="emit('close')"
      >
        <div
          ref="dialogRef"
          class="modal-dialog"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
        >
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="modal-close" @click="emit('close')" aria-label="Cerrar">
              <X :size="18" :stroke-width="2" />
            </button>
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
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal, 1000);
}

.modal-dialog {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 520px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  outline: none;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.btn {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

/* ── Modal transition ── */
.modal-enter-active {
  transition: opacity var(--duration-base) var(--ease-out);
}

.modal-enter-active .modal-dialog {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-spring);
}

.modal-leave-active {
  transition: opacity var(--duration-fast) ease-in;
}

.modal-leave-active .modal-dialog {
  transition: opacity var(--duration-fast) ease-in,
              transform var(--duration-fast) ease-in;
}

.modal-enter-from {
  opacity: 0;
}

.modal-enter-from .modal-dialog {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}

.modal-leave-to {
  opacity: 0;
}

.modal-leave-to .modal-dialog {
  opacity: 0;
  transform: scale(0.97);
}
</style>
