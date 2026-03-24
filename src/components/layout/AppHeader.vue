<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import TrayStatus from './TrayStatus.vue';
import NotificationBell from '../shared/NotificationBell.vue';

const route = useRoute();

const titles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/review': 'Revisar Día',
  '/issues': 'Tareas',
  '/merge-requests': 'Merge Requests',
  '/discover': 'Descubrir',
  '/timesheets': 'Parte de horas',
  '/settings': 'Ajustes',
};

const pageTitle = computed(() => titles[route.path] ?? 'Mimir');
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <h1 class="page-title">{{ pageTitle }}</h1>
    </div>
    <div class="header-actions">
      <NotificationBell />
      <TrayStatus />
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 56px;
  padding: 0 var(--space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
  position: relative;
  z-index: var(--z-header);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.page-title {
  font-size: var(--text-lg);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
