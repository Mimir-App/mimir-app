<script setup lang="ts">
withDefaults(defineProps<{
  text?: string;
}>(), {
  text: 'Sin datos que mostrar',
});
</script>

<template>
  <div class="empty-state">{{ text }}</div>
</template>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
