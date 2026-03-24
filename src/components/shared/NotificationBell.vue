<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import type { AppNotification } from '../../lib/types';
import { api } from '../../lib/api';
import {
  Bell,
  MessageCircle,
  XCircle,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  ClipboardList,
} from 'lucide-vue-next';

const router = useRouter();

const unreadCount = ref(0);
const open = ref(false);
const notifications = ref<AppNotification[]>([]);
const loading = ref(false);

let pollTimer: ReturnType<typeof setInterval> | null = null;

const typeIconMap: Record<string, any> = {
  comment: MessageCircle,
  pipeline_failed: XCircle,
  mr_approved: CheckCircle2,
  changes_requested: RefreshCw,
  conflict: AlertTriangle,
  todo: ClipboardList,
};

const typeColorMap: Record<string, string> = {
  comment: 'var(--info)',
  pipeline_failed: 'var(--error)',
  mr_approved: 'var(--success)',
  changes_requested: 'var(--warning)',
  conflict: 'var(--warning)',
  todo: 'var(--text-secondary)',
};

function getIcon(type: string) {
  return typeIconMap[type] ?? Bell;
}

function getColor(type: string) {
  return typeColorMap[type] ?? 'var(--text-secondary)';
}

async function fetchCount() {
  try {
    const result = await api.getNotificationCount();
    unreadCount.value = result.count;
  } catch {
    // sin conexion: no crashing
  }
}

async function openDropdown() {
  open.value = !open.value;
  if (open.value) {
    loading.value = true;
    try {
      notifications.value = await api.getNotifications(true);
    } catch {
      notifications.value = [];
    } finally {
      loading.value = false;
    }
  }
}

async function markAllRead() {
  try {
    await api.markAllNotificationsRead();
    notifications.value = [];
    unreadCount.value = 0;
  } catch {
    // silencioso
  }
}

async function handleClick(n: AppNotification) {
  try {
    await api.markNotificationRead(n.id);
  } catch {
    // silencioso
  }
  notifications.value = notifications.value.filter(x => x.id !== n.id);
  unreadCount.value = Math.max(0, unreadCount.value - 1);
  open.value = false;

  if (n.link) {
    if (n.link.startsWith('http')) {
      window.open(n.link, '_blank');
    } else {
      router.push(n.link);
    }
  }
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'ahora mismo';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}

function onClickOutside(e: MouseEvent) {
  const el = document.getElementById('notification-bell-root');
  if (el && !el.contains(e.target as Node)) {
    open.value = false;
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    open.value = false;
  }
}

onMounted(() => {
  fetchCount();
  pollTimer = setInterval(fetchCount, 30_000);
  document.addEventListener('click', onClickOutside, true);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  document.removeEventListener('click', onClickOutside, true);
});
</script>

<template>
  <div id="notification-bell-root" class="notification-bell" @keydown="handleKeydown">
    <button
      class="bell-btn"
      @click="openDropdown"
      :aria-label="unreadCount > 0 ? `${unreadCount} notificaciones sin leer` : 'Notificaciones'"
      aria-haspopup="true"
      :aria-expanded="open"
    >
      <Bell :size="18" :stroke-width="1.75" />
      <span v-if="unreadCount > 0" class="badge" aria-hidden="true">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <Transition name="dropdown">
      <div v-if="open" class="dropdown" role="menu" aria-label="Notificaciones">
        <div class="dropdown-header">
          <span class="dropdown-title">Notificaciones</span>
          <button
            v-if="notifications.length > 0"
            class="mark-all-btn"
            @click="markAllRead"
          >
            Marcar todas como leidas
          </button>
        </div>

        <div v-if="loading" class="dropdown-empty" role="status">Cargando...</div>
        <div v-else-if="notifications.length === 0" class="dropdown-empty">Sin notificaciones nuevas</div>
        <ul v-else class="notification-list">
          <li
            v-for="n in notifications"
            :key="n.id"
            class="notification-item"
            :class="{ unread: !n.read, clickable: !!n.link }"
            role="menuitem"
            :tabindex="n.link ? 0 : -1"
            @click="handleClick(n)"
            @keydown.enter="handleClick(n)"
          >
            <span class="notif-icon" :style="{ color: getColor(n.type) }" aria-hidden="true">
              <component :is="getIcon(n.type)" :size="16" :stroke-width="1.75" />
            </span>
            <div class="notif-body">
              <p class="notif-title">{{ n.title }}</p>
              <p v-if="n.body" class="notif-text">{{ n.body }}</p>
              <p class="notif-time">{{ relativeTime(n.created_at) }}</p>
            </div>
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notification-bell {
  position: relative;
  display: flex;
  align-items: center;
}

.bell-btn {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-1) 6px;
  border-radius: var(--radius-md);
  line-height: 1;
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-out);
}

.bell-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.badge {
  position: absolute;
  top: 0;
  right: 0;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
  line-height: 1;
  pointer-events: none;
}

/* ── Dropdown ── */
.dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 340px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown);
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.dropdown-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.mark-all-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--text-xs);
  color: var(--accent);
  padding: 0;
  transition: opacity var(--duration-fast);
}

.mark-all-btn:hover {
  opacity: 0.8;
}

.dropdown-empty {
  padding: var(--space-5) var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.notification-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  transition: background var(--duration-fast);
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item.clickable {
  cursor: pointer;
}

.notification-item.clickable:hover {
  background: var(--bg-hover);
}

.notification-item.unread {
  background: var(--accent-soft);
}

.notification-item.unread.clickable:hover {
  background: rgba(203, 27, 33, 0.15);
}

.notif-icon {
  flex-shrink: 0;
  margin-top: 2px;
  display: flex;
}

.notif-body {
  flex: 1;
  min-width: 0;
}

.notif-title {
  margin: 0 0 2px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notif-text {
  margin: 0 0 2px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-time {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* ── Dropdown transition ── */
.dropdown-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out);
}

.dropdown-leave-active {
  transition: opacity var(--duration-fast) ease-in,
              transform var(--duration-fast) ease-in;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
</style>
