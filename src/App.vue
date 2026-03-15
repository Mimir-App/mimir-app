<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue';
import AppSidebar from './components/layout/AppSidebar.vue';
import AppHeader from './components/layout/AppHeader.vue';
import { useDaemonStore } from './stores/daemon';
import { useConfigStore } from './stores/config';

const daemonStore = useDaemonStore();
const configStore = useConfigStore();

let pollTimer: ReturnType<typeof setInterval> | null = null;

function handleZoom(e: KeyboardEvent) {
  if (!e.ctrlKey && !e.metaKey) return;
  if (e.key === '+' || e.key === '=') {
    e.preventDefault();
    configStore.config.font_size = Math.min(configStore.config.font_size + 1, 22);
  } else if (e.key === '-') {
    e.preventDefault();
    configStore.config.font_size = Math.max(configStore.config.font_size - 1, 10);
  } else if (e.key === '0') {
    e.preventDefault();
    configStore.config.font_size = 14;
  }
}

function applyTheme(theme: string) {
  const resolved = theme === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme;
  document.documentElement.setAttribute('data-theme', resolved);
}

function applyZoomLevel(size: number) {
  const zoomPercent = Math.round((size / 14) * 100);
  const layout = document.querySelector('.app-layout') as HTMLElement | null;
  if (layout) layout.style.zoom = `${zoomPercent}%`;
}

onMounted(async () => {
  window.addEventListener('keydown', handleZoom);
  await configStore.load();
  applyTheme(configStore.config.theme);
  applyZoomLevel(configStore.config.font_size);

  // Health check de ambos procesos
  await daemonStore.captureHealthCheck();
  const ok = await daemonStore.healthCheck();
  if (ok) {
    configStore.pushToDaemon();
  }

  pollTimer = setInterval(() => {
    daemonStore.fetchStatus();
    daemonStore.captureHealthCheck();
  }, 10000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  window.removeEventListener('keydown', handleZoom);
});

watch(() => configStore.config.theme, (theme) => {
  applyTheme(theme);
});

watch(() => configStore.config.font_size, (size) => {
  applyZoomLevel(size);
});
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="app-main">
      <AppHeader />
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style>
:root {
  color-scheme: dark;
  --bg-primary: #1e2029;
  --bg-secondary: #2d2d33;
  --bg-card: #383840;
  --bg-hover: #3d3d46;
  --text-primary: #f0f0f0;
  --text-secondary: #a2b0b4;
  --accent: #cb1b21;
  --accent-hover: #a51519;
  --selection: rgba(203, 27, 33, 0.15);
  --success: #4ec9b0;
  --warning: #dcdcaa;
  --error: #f14c4c;
  --border: #3d3d46;
}

[data-theme="light"] {
  color-scheme: light;
  --bg-primary: #f8f9fa;
  --bg-secondary: #ffffff;
  --bg-card: #f3f4f6;
  --bg-hover: #e5e7eb;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --accent: #cb1b21;
  --accent-hover: #a51519;
  --selection: rgba(203, 27, 33, 0.1);
  --success: #059669;
  --warning: #d97706;
  --error: #dc2626;
  --border: #d1d5db;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

select, input, textarea {
  font-family: inherit;
  font-size: inherit;
  color: var(--text-primary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 8px;
}

select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23a2b0b4' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 24px;
}

select option {
  background: var(--bg-card);
  color: var(--text-primary);
}

th.sortable {
  cursor: pointer;
  user-select: none;
}

th.sortable:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.btn-collapse {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  white-space: nowrap;
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-collapse:hover {
  color: var(--text-primary);
  border-color: var(--accent);
  background: var(--bg-hover);
}

.collapse-icon {
  font-size: 9px;
  transition: transform 0.15s;
}

.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  padding: 16px;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
