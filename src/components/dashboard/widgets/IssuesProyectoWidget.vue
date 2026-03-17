<script setup lang="ts">
defineProps<{
  config: Record<string, any>;
}>();
</script>

<template>
  <div class="placeholder-widget">
    <h3 class="card-title">Issues por Proyecto</h3>
    <div class="placeholder-content">
      <span class="placeholder-text">Proximamente</span>
    </div>
  </div>
</template>

<style scoped>
.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.placeholder-content {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.placeholder-text {
  font-size: 14px;
  color: var(--text-secondary);
  opacity: 0.5;
  font-style: italic;
}
</style>
