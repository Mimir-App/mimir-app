<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useDaemonStore } from '../../../stores/daemon';
import { formatHours, formatTime } from '../../../composables/useFormatting';
import { api } from '../../../lib/api';

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
  <h3 class="card-title">Jornada</h3>
  <div v-if="!attendance.checkIn" class="attendance-empty">
    <button class="btn-attendance checkin" @click="checkIn" :disabled="attendanceLoading || !daemonStore.connected">
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
    <div class="att-row">
      <span class="att-label">Duracion</span>
      <span class="att-time" :class="{ active: isCheckedIn }">{{ formatHours(workDuration) }}</span>
    </div>
    <div class="att-actions" v-if="isCheckedIn">
      <button class="btn-attendance checkout" @click="checkOut" :disabled="attendanceLoading">
        {{ attendanceLoading ? 'Fichando...' : 'Fichar salida' }}
      </button>
    </div>
    <div v-if="isCheckedOut" class="att-hint">Jornada finalizada</div>
  </div>
</template>

<style scoped>
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.attendance-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 12px 0; }
.btn-attendance { padding: 10px 24px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s; }
.btn-attendance:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-attendance.checkin { background: var(--success); color: white; }
.btn-attendance.checkin:hover:not(:disabled) { opacity: 0.85; }
.btn-attendance.checkout { background: var(--accent); color: white; }
.btn-attendance.checkout:hover:not(:disabled) { background: var(--accent-hover); }
.attendance-info { display: flex; flex-direction: column; gap: 6px; }
.att-row { display: flex; justify-content: space-between; font-size: 13px; }
.att-label { color: var(--text-secondary); }
.att-time { font-weight: 500; }
.att-time.active { color: var(--success); }
.att-actions { display: flex; justify-content: center; margin-top: 6px; }
.att-hint { font-size: 11px; color: var(--text-secondary); text-align: center; margin-top: 4px; }
</style>
