<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AppSidebar from './components/layout/AppSidebar.vue';
import AppHeader from './components/layout/AppHeader.vue';
import { useDaemonStore } from './stores/daemon';
import { useConfigStore } from './stores/config';
import { useOdooStore } from './stores/odoo';

const route = useRoute();
const router = useRouter();
const daemonStore = useDaemonStore();
const configStore = useConfigStore();
const odooStore = useOdooStore();

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
  document.body.style.zoom = `${zoomPercent}%`;
}

onMounted(async () => {
  window.addEventListener('keydown', handleZoom);
  await configStore.load();
  applyTheme(configStore.config.theme);
  applyZoomLevel(configStore.config.font_size);

  // Redirect a onboarding si no se ha completado
  if (!configStore.config.onboarding_completed && route.path !== '/onboarding') {
    router.push('/onboarding');
  }

  // Health check de ambos procesos + push config con retry
  await daemonStore.captureHealthCheck();
  let ok = await daemonStore.healthCheck();
  if (!ok) {
    // Server puede tardar en arrancar, reintentar
    for (let i = 0; i < 5 && !ok; i++) {
      await new Promise(r => window.setTimeout(r, 1000));
      ok = await daemonStore.healthCheck();
    }
  }
  if (ok) {
    await configStore.pushToDaemon();
    // Iniciar cache de proyectos Odoo con refresh periodico
    odooStore.startPolling();
    odooStore.watchConfig();
  }

  pollTimer = setInterval(() => {
    daemonStore.fetchStatus();
    daemonStore.captureHealthCheck();
  }, 10000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  odooStore.stopPolling();
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
  <div v-if="route.path === '/onboarding'">
    <router-view />
  </div>
  <div v-else class="app-layout">
    <AppSidebar />
    <div class="app-main">
      <AppHeader />
      <div v-if="daemonStore.versionMismatch" class="version-mismatch-banner" role="alert">
        Capture (v{{ daemonStore.captureVersion }}) y Server (v{{ daemonStore.serverVersion }}) tienen versiones distintas.
        Actualiza mimir-capture: <code>sudo dpkg -i mimir-capture_{{ daemonStore.serverVersion }}_amd64.deb</code>
      </div>
      <main class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style>
/* ═══════════════════════════════════════════════
   MIMIR DESIGN SYSTEM v2
   ═══════════════════════════════════════════════ */

:root {
  color-scheme: dark;

  /* ── Palette ── */
  --bg-primary: #13141a;
  --bg-secondary: #1c1d26;
  --bg-card: #242530;
  --bg-hover: #2e2f3a;
  --bg-elevated: #2a2b36;
  --text-primary: #eaedf0;
  --text-secondary: #8b919e;
  --text-muted: #7a7f8e;
  --accent: #cb1b21;
  --accent-hover: #e02028;
  --accent-soft: rgba(203, 27, 33, 0.12);
  --accent-glow: rgba(203, 27, 33, 0.25);
  --selection: rgba(203, 27, 33, 0.15);
  --success: #34d399;
  --success-soft: rgba(52, 211, 153, 0.12);
  --warning: #fbbf24;
  --warning-soft: rgba(251, 191, 36, 0.12);
  --error: #f87171;
  --error-soft: rgba(248, 113, 113, 0.12);
  --info: #60a5fa;
  --info-soft: rgba(96, 165, 250, 0.12);
  --border: #2e2f3a;
  --border-subtle: #252630;

  /* ── Glass ── */
  --glass-bg: rgba(28, 29, 38, 0.75);
  --glass-border: rgba(255, 255, 255, 0.06);
  --glass-blur: 16px;

  /* ── Shadows ── */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 8px 30px rgba(0, 0, 0, 0.4);
  --shadow-glow: 0 0 20px var(--accent-glow);

  /* ── Typography ── */
  --font-sans: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --text-xs: 0.6875rem;   /* 11px */
  --text-sm: 0.8125rem;   /* 13px */
  --text-base: 0.875rem;  /* 14px */
  --text-lg: 1rem;        /* 16px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 2rem;       /* 32px */

  /* ── Spacing scale ── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* ── Radii ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* ── Z-index scale ── */
  --z-base: 0;
  --z-header: 10;
  --z-sidebar: 20;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-overlay: 900;
  --z-modal: 1000;
  --z-toast: 1100;

  /* ── Transitions ── */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --duration-fast: 120ms;
  --duration-base: 200ms;
  --duration-slow: 350ms;

  /* ── Focus ring ── */
  --focus-ring: 0 0 0 2px var(--bg-primary), 0 0 0 4px var(--accent);
}

[data-theme="light"] {
  color-scheme: light;
  --bg-primary: #f5f6f8;
  --bg-secondary: #ffffff;
  --bg-card: #f0f1f4;
  --bg-hover: #e8e9ee;
  --bg-elevated: #ffffff;
  --text-primary: #1a1d26;
  --text-secondary: #6b7280;
  --text-muted: #8b919e;
  --accent: #cb1b21;
  --accent-hover: #b31820;
  --accent-soft: rgba(203, 27, 33, 0.08);
  --accent-glow: rgba(203, 27, 33, 0.15);
  --selection: rgba(203, 27, 33, 0.08);
  --success: #059669;
  --success-soft: rgba(5, 150, 105, 0.08);
  --warning: #d97706;
  --warning-soft: rgba(217, 119, 6, 0.08);
  --error: #dc2626;
  --error-soft: rgba(220, 38, 38, 0.08);
  --info: #2563eb;
  --info-soft: rgba(37, 99, 235, 0.08);
  --border: #e2e4e9;
  --border-subtle: #eef0f3;
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(0, 0, 0, 0.06);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 30px rgba(0, 0, 0, 0.12);
  --shadow-glow: 0 0 20px rgba(203, 27, 33, 0.1);
  --focus-ring: 0 0 0 2px var(--bg-primary), 0 0 0 4px var(--accent);
}

/* ── Reset ── */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* ── Base ── */
body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Form elements ── */
select, input, textarea {
  font-family: inherit;
  font-size: inherit;
  color: var(--text-primary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  transition: border-color var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%238b919e' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
}

select option {
  background: var(--bg-card);
  color: var(--text-primary);
}

/* ── Sortable headers ── */
th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color var(--duration-fast), background var(--duration-fast);
}

th.sortable:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

/* ── Collapse button ── */
.btn-collapse {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out);
}

.btn-collapse:hover {
  color: var(--text-primary);
  border-color: var(--accent);
  background: var(--accent-soft);
}

.collapse-icon {
  font-size: 9px;
  transition: transform var(--duration-base) var(--ease-out);
}

/* ── Layout ── */
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
  background: var(--bg-primary);
}

.version-mismatch-banner {
  padding: var(--space-2) var(--space-4);
  background: var(--warning-soft);
  border-bottom: 1px solid var(--warning);
  color: var(--warning);
  font-size: var(--text-sm);
  text-align: center;
  flex-shrink: 0;
}

.version-mismatch-banner code {
  background: var(--bg-card);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.app-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  padding: var(--space-5);
}

/* ── Page transitions ── */
.page-enter-active {
  transition: opacity var(--duration-slow) var(--ease-out),
              transform var(--duration-slow) var(--ease-out);
}
.page-leave-active {
  transition: opacity var(--duration-fast) ease-in;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* ── Selection ── */
::selection {
  background: var(--accent-soft);
  color: var(--text-primary);
}

/* ── Global focus-visible ── */
:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* ── Global active/pressed state ── */
button:active:not(:disabled),
[role="button"]:active:not(:disabled) {
  transform: scale(0.97);
  transition-duration: 50ms;
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  .page-enter-active,
  .page-leave-active {
    transition: none;
  }

  .page-enter-from {
    transform: none;
  }
}
</style>
