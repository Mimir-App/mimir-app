<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDaemonStore } from '../../stores/daemon';

const route = useRoute();
const router = useRouter();
const daemonStore = useDaemonStore();
const collapsed = ref(false);

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { path: '/review', label: 'Revisar Dia', icon: '✓' },
  { path: '/issues', label: 'Issues', icon: '◉' },
  { path: '/merge-requests', label: 'MRs', icon: '⑂' },
  { path: '/timesheets', label: 'Parte de horas', icon: '⏱' },
  { path: '/settings', label: 'Ajustes', icon: '⚙' },
];

const currentPath = computed(() => route.path);

function navigate(path: string) {
  router.push(path);
}

function toggleCollapse() {
  collapsed.value = !collapsed.value;
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-header" @click="toggleCollapse" title="Colapsar/expandir sidebar">
      <img src="../../assets/mimir-silhouette.svg" alt="Mimir" class="logo-icon" />
      <span v-if="!collapsed" class="logo-text">Mimir</span>
    </div>

    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        :title="collapsed ? item.label : undefined"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="daemon-status" :class="daemonStore.statusClass" :title="daemonStore.statusText">
        <span class="status-dot"></span>
        <span v-if="!collapsed" class="status-text">{{ daemonStore.statusText }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s ease;
}

.sidebar.collapsed {
  width: 52px;
}

.sidebar-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}

.sidebar.collapsed .sidebar-header {
  padding: 0;
  justify-content: center;
}

.sidebar-header:hover {
  background: var(--bg-hover);
}

.logo-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-nav {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar.collapsed .sidebar-nav {
  padding: 8px 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  font-size: 13px;
  text-align: left;
  width: 100%;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar.collapsed .nav-item {
  padding: 8px 0;
  justify-content: center;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--selection);
  color: var(--accent);
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border);
}

.sidebar.collapsed .sidebar-footer {
  padding: 12px 4px;
  display: flex;
  justify-content: center;
}

.daemon-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.sidebar.collapsed .daemon-status {
  justify-content: center;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-secondary);
  flex-shrink: 0;
}

.daemon-status.connected .status-dot {
  background: var(--success);
}

.daemon-status.disconnected .status-dot {
  background: var(--error);
}

.status-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
