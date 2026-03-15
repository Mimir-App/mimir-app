<script setup lang="ts">
withDefaults(defineProps<{
  text?: string;
}>(), {
  text: 'Cargando...',
});
</script>

<template>
  <div class="loading-state">{{ text }}</div>
</template>

<style scoped>
.loading-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
