<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
const route = useRoute();

const titles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/review': 'Revisar Día',
  '/issues': 'Issues',
  '/merge-requests': 'Merge Requests',
  '/timesheets': 'Timesheets',
  '/settings': 'Ajustes',
};

const pageTitle = computed(() => titles[route.path] ?? 'Mimir');
</script>

<template>
  <header class="app-header">
    <h1 class="page-title">{{ pageTitle }}</h1>
    <div class="header-actions">
      <TrayStatus />
    </div>
  </header>
</template>

<script lang="ts">
import TrayStatus from './TrayStatus.vue';
</script>

<style scoped>
.app-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
}
</style>
