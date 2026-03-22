<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useDaemonStore } from '../../../stores/daemon';
import { formatHours, formatTime } from '../../../composables/useFormatting';
import { api } from '../../../lib/api';
import { LogIn, LogOut } from 'lucide-vue-next';

defineProps<{ config: Record<string, any> }>();

const daemonStore = useDaemonStore();

interface Attendance { id: number | null; checkIn: string | null; checkOut: string | null; }

const attendance = ref<Attendance>({ id: null, checkIn: null, checkOut: null });
const attendanceLoading = ref(false);
const isCheckedIn = computed(() => attendance.value.checkIn !== null && attendance.value.checkOut === null);
const isCheckedOut = computed(() => attendance.value.checkIn !== null && attendance.value.checkOut !== null);

const workDuration = computed(() => {
  if (!attendance.value.checkIn) return 0;
  const start = new Date(attendance.value.checkIn).getTime();
  const end = attendance.value.checkOut ? new Date(attendance.value.checkOut).getTime() : Date.now();
  return (end - start) / (1000 * 60 * 60);
});

async function fetchAttendance() {
  if (!daemonStore.connected) return;
  try {
    const result = await api.getAttendanceToday() as { attendance: { id: number; check_in: string; check_out: string | false | null } | null };
    if (result.attendance) {
      attendance.value = {
        id: result.attendance.id,
        checkIn: result.attendance.check_in || null,
        checkOut: result.attendance.check_out || null,
      };
    } else {
      attendance.value = { id: null, checkIn: null, checkOut: null };
    }
  } catch { attendance.value = { id: null, checkIn: null, checkOut: null }; }
}

async function checkIn() {
  attendanceLoading.value = true;
  try {
    const result = await api.attendanceCheckIn() as { id: number };
    attendance.value = { id: result.id, checkIn: new Date().toISOString(), checkOut: null };
  } catch { /* ignore */ }
  finally { attendanceLoading.value = false; }
}

async function checkOut() {
  if (!attendance.value.id) return;
  attendanceLoading.value = true;
  try {
    await api.attendanceCheckOut(attendance.value.id);
    attendance.value.checkOut = new Date().toISOString();
  } catch { /* ignore */ }
  finally { attendanceLoading.value = false; }
}

onMounted(() => fetchAttendance());
</script>

<template>
  <div class="widget-jornada">
    <h3 class="widget-title">Jornada</h3>

    <div v-if="!attendance.checkIn" class="attendance-empty">
      <button class="btn-attendance checkin" @click="checkIn" :disabled="attendanceLoading || !daemonStore.connected">
        <LogIn :size="18" :stroke-width="2" />
        {{ attendanceLoading ? 'Fichando...' : 'Fichar entrada' }}
      </button>
      <span v-if="!daemonStore.connected" class="att-hint">Servidor no conectado</span>
    </div>

    <div v-else class="attendance-info">
      <div class="att-row">
        <span class="att-label">Entrada</span>
        <span class="att-time">{{ formatTime(attendance.checkIn!) }}</span>
      </div>
      <div class="att-row" v-if="attendance.checkOut">
        <span class="att-label">Salida</span>
        <span class="att-time">{{ formatTime(attendance.checkOut) }}</span>
      </div>
      <div class="att-row duration">
        <span class="att-label">Duración</span>
        <span class="att-time" :class="{ active: isCheckedIn }">{{ formatHours(workDuration) }}</span>
      </div>
      <div class="att-actions" v-if="isCheckedIn">
        <button class="btn-attendance checkout" @click="checkOut" :disabled="attendanceLoading">
          <LogOut :size="16" :stroke-width="2" />
          {{ attendanceLoading ? 'Fichando...' : 'Fichar salida' }}
        </button>
      </div>
      <div v-if="isCheckedOut" class="att-done">Jornada finalizada</div>
    </div>
  </div>
</template>

<style scoped>
.widget-jornada {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.widget-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.attendance-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) 0;
}

.btn-attendance {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all var(--duration-base) var(--ease-out);
}

.btn-attendance:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-attendance.checkin {
  background: linear-gradient(135deg, var(--success) 0%, #2dd4bf 100%);
  color: #0f1a14;
  box-shadow: 0 4px 14px rgba(52, 211, 153, 0.3);
}

.btn-attendance.checkin:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(52, 211, 153, 0.4);
}

.btn-attendance.checkout {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
  color: white;
  box-shadow: 0 4px 14px var(--accent-glow);
}

.btn-attendance.checkout:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--accent-glow);
}

.attendance-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.att-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
  padding: var(--space-1) 0;
}

.att-row.duration {
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  margin-top: var(--space-1);
}

.att-label {
  color: var(--text-secondary);
  font-weight: 400;
}

.att-time {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.att-time.active {
  color: var(--success);
}

.att-actions {
  display: flex;
  justify-content: center;
  margin-top: var(--space-2);
}

.att-done {
  font-size: var(--text-xs);
  color: var(--success);
  text-align: center;
  font-weight: 500;
  padding: var(--space-1) var(--space-2);
  background: var(--success-soft);
  border-radius: var(--radius-sm);
}

.att-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
