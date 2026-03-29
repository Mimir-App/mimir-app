<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDaemonStore } from '../../stores/daemon';
import { useConfigStore } from '../../stores/config';
import {
  LayoutDashboard,
  ClipboardCheck,
  CircleDot,
  GitBranch,
  Compass,
  Clock,
  Settings,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const daemonStore = useDaemonStore();
const configStore = useConfigStore();
const collapsed = ref(false);

const allNavItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, configKey: 'section_dashboard' as const },
  { path: '/review', label: 'Revisar Día', icon: ClipboardCheck, configKey: null },
  { path: '/issues', label: 'Tareas', icon: CircleDot, configKey: 'section_issues' as const },
  { path: '/merge-requests', label: 'Ramas', icon: GitBranch, configKey: 'section_merge_requests' as const },
  { path: '/discover', label: 'Descubrir', icon: Compass, configKey: 'section_discover' as const },
  { path: '/timesheets', label: 'Parte de horas', icon: Clock, configKey: 'section_timesheets' as const },
  { path: '/settings', label: 'Ajustes', icon: Settings, configKey: null },
];

const navItems = computed(() =>
  allNavItems.filter(item => !item.configKey || configStore.config[item.configKey])
);

const currentPath = computed(() => route.path);

function navigate(path: string) {
  router.push(path);
}

function toggleCollapse() {
  collapsed.value = !collapsed.value;
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }" role="navigation" aria-label="Navegacion principal">
    <div class="sidebar-header" @click="toggleCollapse" role="button" tabindex="0" :aria-label="collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'" @keydown.enter="toggleCollapse" @keydown.space.prevent="toggleCollapse">
      <div class="logo-mark">
        <img src="../../assets/mimir-silhouette.svg" alt="Mimir" class="logo-icon" />
      </div>
      <transition name="fade">
        <span v-if="!collapsed" class="logo-text">Mimir</span>
      </transition>
    </div>

    <nav class="sidebar-nav" aria-label="Menu principal">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        :title="collapsed ? item.label : undefined"
        :aria-label="item.label"
        :aria-current="currentPath === item.path ? 'page' : undefined"
        @click="navigate(item.path)"
      >
        <span class="nav-indicator" aria-hidden="true"></span>
        <component :is="item.icon" class="nav-icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
        <transition name="fade">
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        </transition>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="daemon-status" :class="daemonStore.statusClass" :title="daemonStore.statusText" role="status" aria-live="polite">
        <span class="status-dot" aria-hidden="true"></span>
        <transition name="fade">
          <span v-if="!collapsed" class="status-text">{{ daemonStore.statusText }}</span>
        </transition>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 210px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-right: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width var(--duration-slow) var(--ease-out);
  position: relative;
  z-index: var(--z-sidebar);
}

.sidebar.collapsed {
  width: 56px;
}

/* ── Header ── */
.sidebar-header {
  height: 56px;
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  border-bottom: 1px solid var(--glass-border);
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out);
}

.sidebar.collapsed .sidebar-header {
  padding: 0;
  justify-content: center;
}

.sidebar-header:hover {
  background: var(--bg-hover);
}

.logo-mark {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-icon {
  width: 26px;
  height: 26px;
}

.logo-text {
  font-weight: 700;
  font-size: var(--text-lg);
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── Navigation ── */
.sidebar-nav {
  flex: 1;
  padding: var(--space-3) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.sidebar.collapsed .sidebar-nav {
  padding: var(--space-3) var(--space-1);
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 400;
  text-align: left;
  width: 100%;
  transition: all var(--duration-base) var(--ease-out);
  white-space: nowrap;
  overflow: hidden;
}

.sidebar.collapsed .nav-item {
  padding: var(--space-2) 0;
  justify-content: center;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 500;
}

/* Indicador lateral activo */
.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
  transition: transform var(--duration-base) var(--ease-spring);
}

.nav-item.active .nav-indicator {
  transform: translateY(-50%) scaleY(1);
}

.nav-icon {
  flex-shrink: 0;
  transition: color var(--duration-fast);
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Footer ── */
.sidebar-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--glass-border);
}

.sidebar.collapsed .sidebar-footer {
  padding: var(--space-3) var(--space-1);
  display: flex;
  justify-content: center;
}

.daemon-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.sidebar.collapsed .daemon-status {
  justify-content: center;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
  transition: background var(--duration-base), box-shadow var(--duration-base);
}

.daemon-status.connected .status-dot {
  background: var(--success);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.4);
}

.daemon-status.disconnected .status-dot {
  background: var(--error);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.3);
}

.status-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Fade transition for labels ── */
.fade-enter-active {
  transition: opacity var(--duration-base) var(--ease-out);
}
.fade-leave-active {
  transition: opacity var(--duration-fast);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
