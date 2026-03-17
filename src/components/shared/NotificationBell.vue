<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import type { AppNotification } from '../../lib/types';
import { api } from '../../lib/api';

const router = useRouter();

const unreadCount = ref(0);
const open = ref(false);
const notifications = ref<AppNotification[]>([]);
const loading = ref(false);

let pollTimer: ReturnType<typeof setInterval> | null = null;

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

function typeIcon(type: string): string {
  const map: Record<string, string> = {
    comment: '💬',
    pipeline_failed: '❌',
    mr_approved: '✅',
    changes_requested: '🔄',
    conflict: '⚠️',
    todo: '📋',
  };
  return map[type] ?? '🔔';
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
  <div id="notification-bell-root" class="notification-bell">
    <button class="bell-btn" @click="openDropdown" :title="unreadCount > 0 ? `${unreadCount} notificaciones sin leer` : 'Notificaciones'">
      <span class="bell-icon">🔔</span>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <div v-if="open" class="dropdown">
      <div class="dropdown-header">
        <span class="dropdown-title">Notificaciones</span>
        <button v-if="notifications.length > 0" class="mark-all-btn" @click="markAllRead">
          Marcar todas como leidas
        </button>
      </div>

      <div v-if="loading" class="dropdown-empty">Cargando...</div>
      <div v-else-if="notifications.length === 0" class="dropdown-empty">Sin notificaciones nuevas</div>
      <ul v-else class="notification-list">
        <li
          v-for="n in notifications"
          :key="n.id"
          class="notification-item"
          :class="{ unread: !n.read, clickable: !!n.link }"
          @click="handleClick(n)"
        >
          <span class="notif-icon">{{ typeIcon(n.type) }}</span>
          <div class="notif-body">
            <p class="notif-title">{{ n.title }}</p>
            <p v-if="n.body" class="notif-text">{{ n.body }}</p>
            <p class="notif-time">{{ relativeTime(n.created_at) }}</p>
          </div>
        </li>
      </ul>
    </div>
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
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  transition: background 0.15s;
}

.bell-btn:hover {
  background: var(--bg-card, rgba(255,255,255,0.08));
}

.bell-icon {
  display: block;
}

.badge {
  position: absolute;
  top: 0;
  right: 0;
  background: var(--accent, #cb1b21);
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

/* Dropdown */
.dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  background: var(--bg-secondary, #2d2d33);
  border: 1px solid var(--border, #3d3d46);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  z-index: 999;
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border, #3d3d46);
}

.dropdown-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #f0f0f0);
}

.mark-all-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 11px;
  color: var(--accent, #cb1b21);
  padding: 0;
}

.mark-all-btn:hover {
  text-decoration: underline;
}

.dropdown-empty {
  padding: 20px 14px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary, #a2b0b4);
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
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border, #3d3d46);
  transition: background 0.12s;
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item.clickable {
  cursor: pointer;
}

.notification-item.clickable:hover {
  background: var(--bg-card, rgba(255,255,255,0.05));
}

.notification-item.unread {
  background: rgba(203, 27, 33, 0.06);
}

.notification-item.unread.clickable:hover {
  background: rgba(203, 27, 33, 0.12);
}

.notif-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.notif-body {
  flex: 1;
  min-width: 0;
}

.notif-title {
  margin: 0 0 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #f0f0f0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notif-text {
  margin: 0 0 2px;
  font-size: 11px;
  color: var(--text-secondary, #a2b0b4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-time {
  margin: 0;
  font-size: 11px;
  color: var(--text-secondary, #a2b0b4);
}
</style>
