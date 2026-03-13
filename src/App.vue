<script setup lang="ts">
import AppSidebar from './components/layout/AppSidebar.vue';
import AppHeader from './components/layout/AppHeader.vue';
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
  --bg-primary: #1e1e1e;
  --bg-secondary: #252526;
  --bg-card: #2d2d2d;
  --bg-hover: #383838;
  --text-primary: #cccccc;
  --text-secondary: #858585;
  --accent: #569cd6;
  --accent-hover: #6cb0f0;
  --selection: #264f78;
  --status-bar: #007acc;
  --success: #4ec9b0;
  --warning: #dcdcaa;
  --error: #f14c4c;
  --border: #3e3e3e;
}

[data-theme="light"] {
  --bg-primary: #f8f9fa;
  --bg-secondary: #ffffff;
  --bg-card: #f3f4f6;
  --bg-hover: #e5e7eb;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --accent: #2563eb;
  --accent-hover: #3b82f6;
  --selection: #dbeafe;
  --status-bar: #2563eb;
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
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
