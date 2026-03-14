<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue';
import AppSidebar from './components/layout/AppSidebar.vue';
import AppHeader from './components/layout/AppHeader.vue';
import { useDaemonStore } from './stores/daemon';
import { useConfigStore } from './stores/config';

const daemonStore = useDaemonStore();
const configStore = useConfigStore();

let pollTimer: ReturnType<typeof setInterval> | null = null;

function applyTheme(theme: string) {
  const resolved = theme === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme;
  document.documentElement.setAttribute('data-theme', resolved);
}

onMounted(async () => {
  await configStore.load();
  applyTheme(configStore.config.theme);

  // Health check al arrancar y si el daemon esta disponible, enviar config
  const ok = await daemonStore.healthCheck();
  if (ok) {
    configStore.pushToDaemon();
  }

  pollTimer = setInterval(() => daemonStore.fetchStatus(), 10000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});

watch(() => configStore.config.theme, (theme) => {
  applyTheme(theme);
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

.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-content {
  flex: 1;
  overflow-y: auto;
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
