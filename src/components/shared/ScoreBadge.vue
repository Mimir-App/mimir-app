<script setup lang="ts">
import { ref, computed } from 'vue';

const props = withDefaults(defineProps<{
  score: number;
  editable?: boolean;
  manualScore?: number;
}>(), {
  editable: false,
  manualScore: 0,
});

const emit = defineEmits<{
  'update:manualScore': [value: number];
}>();

const editing = ref(false);
const editValue = ref(0);

const level = computed(() => {
  if (props.score >= 150) return 'critical';
  if (props.score >= 100) return 'high';
  if (props.score >= 50) return 'medium';
  return 'low';
});

function startEdit(e: MouseEvent) {
  if (!props.editable) return;
  e.stopPropagation();
  editValue.value = props.manualScore;
  editing.value = true;
}

function commitEdit() {
  editing.value = false;
  if (editValue.value !== props.manualScore) {
    emit('update:manualScore', editValue.value);
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') commitEdit();
  if (e.key === 'Escape') { editing.value = false; }
}
</script>

<template>
  <span v-if="!editing" class="score-badge" :class="[level, { editable, 'has-manual': manualScore > 0 }]" @click="startEdit" :title="editable ? `Score: ${isNaN(score) ? 0 : score} (manual: ${manualScore}). Click para editar.` : undefined">
    {{ isNaN(score) ? 0 : score }}
  </span>
  <input
    v-else
    v-model.number="editValue"
    type="number"
    class="score-input"
    @blur="commitEdit"
    @keydown="onKeydown"
    @click.stop
    ref="inputEl"
    autofocus
  />
</template>

<style scoped>
.score-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  box-sizing: border-box;
}

.score-badge.editable {
  cursor: pointer;
}

.score-badge.editable:hover {
  outline: 1px dashed var(--text-secondary);
}

.score-badge.has-manual {
  border: 1px solid currentColor;
}

.score-badge.critical {
  background: var(--error-soft);
  color: var(--error);
}

.score-badge.high {
  background: var(--warning-soft);
  color: var(--warning);
}

.score-badge.medium {
  background: var(--info-soft);
  color: var(--accent);
}

.score-badge.low {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.score-input {
  width: 48px;
  padding: 2px 4px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--accent);
  border-radius: 4px;
  outline: none;
}
</style>
