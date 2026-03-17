<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <section class="setting-group">
    <h4 class="setting-group-title">{{ title }}</h4>
    <p v-if="description" class="setting-group-description">{{ description }}</p>
    <slot />
  </section>
</template>

<style scoped>
.setting-group {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.setting-group-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.setting-group-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px;
}
</style>
