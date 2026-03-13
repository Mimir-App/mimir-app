<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDaemonStore } from '../../stores/daemon';

const route = useRoute();
const router = useRouter();
const daemonStore = useDaemonStore();

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { path: '/review', label: 'Revisar Día', icon: '✓' },
  { path: '/issues', label: 'Issues', icon: '◉' },
  { path: '/merge-requests', label: 'MRs', icon: '⑂' },
  { path: '/timesheets', label: 'Timesheets', icon: '⏱' },
  { path: '/settings', label: 'Ajustes', icon: '⚙' },
];

const currentPath = computed(() => route.path);

function navigate(path: string) {
  router.push(path);
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <span class="logo">M</span>
      <span class="logo-text">Mimir</span>
    </div>

    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="daemon-status" :class="daemonStore.statusClass">
        <span class="status-dot"></span>
        <span class="status-text">{{ daemonStore.statusText }}</span>
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
}

.sidebar-header {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--border);
}

.logo {
  width: 32px;
  height: 32px;
  background: var(--accent);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
}

.sidebar-nav {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
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
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border);
}

.daemon-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-secondary);
}

.daemon-status.connected .status-dot {
  background: var(--success);
}

.daemon-status.disconnected .status-dot {
  background: var(--error);
}
</style>
