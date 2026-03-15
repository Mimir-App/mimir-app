<script setup lang="ts">
import { onMounted, computed, ref } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import { useDaemonStore } from '../stores/daemon';
import { useConfigStore } from '../stores/config';
import { useIssuesStore } from '../stores/issues';
import { formatHours, formatDate, formatTime } from '../composables/useFormatting';
import { getTargetForDate, getWeekDates, getMonthlyTarget } from '../composables/useTargets';
import { api } from '../lib/api';
import type { TimesheetEntry } from '../lib/types';
import DashboardGrid from '../components/shared/DashboardGrid.vue';
import type { DashboardWidget } from '../components/shared/DashboardGrid.vue';
import EmptyState from '../components/shared/EmptyState.vue';

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();
const configStore = useConfigStore();
const issuesStore = useIssuesStore();

const today = new Date().toISOString().slice(0, 10);
const now = new Date();

// --- Widgets ---

const DEFAULT_WIDGETS: DashboardWidget[] = [
  { id: 'attendance', label: 'Jornada', span: 1, rowSpan: 1 },
  { id: 'progress', label: 'Progreso', span: 2, rowSpan: 1 },
  { id: 'day-hours', label: 'Horas dia', span: 2, rowSpan: 1 },
  { id: 'services', label: 'Servicios', span: 1, rowSpan: 1 },
  { id: 'issues', label: 'Top Issues', span: 3, rowSpan: 1 },
];

const DEFAULT_ORDER = DEFAULT_WIDGETS.map(w => w.id);
const DEFAULT_SPANS: Record<string, [number, number]> = {};

const editing = ref(false);
const editOrder = ref<string[]>([]);
const editSpans = ref<Record<string, [number, number]>>({});

function startEditing() {
  editOrder.value = [...(configStore.config.dashboard_order.length ? configStore.config.dashboard_order : DEFAULT_ORDER)];
  editSpans.value = { ...configStore.config.dashboard_spans };
  editing.value = true;
}

function saveLayout() {
  configStore.config.dashboard_order = editOrder.value;
  configStore.config.dashboard_spans = editSpans.value;
  configStore.save(configStore.config);
  editing.value = false;
}

function resetLayout() {
  editOrder.value = [...DEFAULT_ORDER];
  editSpans.value = { ...DEFAULT_SPANS };
}

function cancelEditing() {
  editing.value = false;
}

function onOrderChange(order: string[]) {
  if (editing.value) {
    editOrder.value = order;
  } else {
    configStore.config.dashboard_order = order;
    configStore.save(configStore.config);
  }
}

function onSpansChange(spans: Record<string, [number, number]>) {
  if (editing.value) {
    editSpans.value = spans;
  } else {
    configStore.config.dashboard_spans = spans;
    configStore.save(configStore.config);
  }
}

const currentOrder = computed(() => editing.value ? editOrder.value : configStore.config.dashboard_order);
const currentSpans = computed(() => editing.value ? editSpans.value : configStore.config.dashboard_spans);

// --- Datos Odoo ---

const odooEntriesToday = ref<TimesheetEntry[]>([]);
const odooEntriesWeek = ref<TimesheetEntry[]>([]);
const odooEntriesMonth = ref<TimesheetEntry[]>([]);

const weekDates = getWeekDates(today);
const weekStart = weekDates[0];
const weekEnd = weekDates[6];
const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
const monthEnd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}`;

// --- Dia (progreso real - siempre hoy) ---

const todayTarget = computed(() => getTargetForDate(today));
const todayOdooHours = computed(() => odooEntriesToday.value.reduce((sum, e) => sum + e.hours, 0));
const todayTotalHours = computed(() => blocksStore.totalHoursToday + todayOdooHours.value);
const todayConfirmedHours = computed(() => blocksStore.confirmedHoursToday + todayOdooHours.value);
const todayUnconfirmedHours = computed(() => blocksStore.unconfirmedHoursToday);

// --- Dia seleccionado (sigue Revisar Dia) ---

const selectedDate = computed(() => blocksStore.selectedDate);
const selectedIsToday = computed(() => selectedDate.value === today);
const selectedTarget = computed(() => getTargetForDate(selectedDate.value));
const selectedOdooHours = computed(() => selectedIsToday.value ? todayOdooHours.value : 0);
const selectedTotalHours = computed(() => blocksStore.totalHoursToday + selectedOdooHours.value);
const selectedConfirmedHours = computed(() => blocksStore.confirmedHoursToday + selectedOdooHours.value);
const selectedUnconfirmedHours = computed(() => blocksStore.unconfirmedHoursToday);
const selectedDateTitle = computed(() => selectedIsToday.value ? 'Horas Hoy' : `Horas ${formatDate(selectedDate.value)}`);

// --- Semana / Mes ---

const weekTarget = computed(() => weekDates.reduce((sum, d) => sum + getTargetForDate(d), 0));
const weekOdooHours = computed(() => odooEntriesWeek.value.reduce((sum, e) => sum + e.hours, 0));
const monthTarget = computed(() => getMonthlyTarget(now.getFullYear(), now.getMonth()));
const monthOdooHours = computed(() => odooEntriesMonth.value.reduce((sum, e) => sum + e.hours, 0));

function progressPct(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min((current / target) * 100, 100);
}

// --- Asistencia (Odoo) ---

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
    const result = await api.getAttendanceToday() as { attendance: { id: number; check_in: string; check_out: string | null } | null };
    if (result.attendance) {
      attendance.value = { id: result.attendance.id, checkIn: result.attendance.check_in, checkOut: result.attendance.check_out };
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

// --- Carga ---

async function fetchOdooData() {
  if (!daemonStore.connected) return;
  try {
    const [dayEntries, weekEntries, monthEntries] = await Promise.all([
      api.getTimesheetEntries(today, today) as Promise<TimesheetEntry[]>,
      api.getTimesheetEntries(weekStart, weekEnd) as Promise<TimesheetEntry[]>,
      api.getTimesheetEntries(monthStart, monthEnd) as Promise<TimesheetEntry[]>,
    ]);
    odooEntriesToday.value = dayEntries;
    odooEntriesWeek.value = weekEntries;
    odooEntriesMonth.value = monthEntries;
  } catch { /* ignore */ }
}

onMounted(() => {
  blocksStore.fetchBlocks();
  issuesStore.fetchIssues();
  fetchOdooData();
  fetchAttendance();
});
</script>

<template>
  <div class="dashboard">
    <!-- Barra de edicion -->
    <div v-if="editing" class="edit-bar">
      <span class="edit-hint">Modo edicion: arrastra widgets para reordenar, pulsa el tamano para cambiar</span>
      <div class="edit-actions">
        <button class="btn-edit reset" @click="resetLayout">Resetear</button>
        <button class="btn-edit cancel" @click="cancelEditing">Cancelar</button>
        <button class="btn-edit save" @click="saveLayout">Guardar</button>
      </div>
    </div>
    <div v-else class="edit-toggle">
      <button class="btn-edit-start" @click="startEditing" title="Editar layout del dashboard">
        &#x270E; Editar dashboard
      </button>
    </div>

    <DashboardGrid
      :widgets="DEFAULT_WIDGETS"
      :order="currentOrder"
      :spans="currentSpans"
      :editing="editing"
      @update:order="onOrderChange"
      @update:spans="onSpansChange"
    >
      <!-- Jornada -->
      <template #attendance>
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

      <!-- Progreso -->
      <template #progress>
        <h3 class="card-title">Progreso</h3>
        <div class="progress-row">
          <span class="progress-label">Hoy</span>
          <div class="progress-bar-wrap">
            <div class="progress-bar">
              <div class="progress-fill confirmed" :style="{ width: progressPct(todayConfirmedHours, todayTarget) + '%' }"></div>
              <div class="progress-fill unconfirmed" :style="{ width: progressPct(todayUnconfirmedHours, todayTarget) + '%' }"></div>
            </div>
          </div>
          <span class="progress-value">{{ formatHours(todayTotalHours) }}</span>
          <span class="progress-target">/ {{ formatHours(todayTarget) }}</span>
        </div>
        <div class="progress-row">
          <span class="progress-label">Semana</span>
          <div class="progress-bar-wrap">
            <div class="progress-bar">
              <div class="progress-fill confirmed" :style="{ width: progressPct(weekOdooHours, weekTarget) + '%' }"></div>
            </div>
          </div>
          <span class="progress-value">{{ formatHours(weekOdooHours) }}</span>
          <span class="progress-target">/ {{ formatHours(weekTarget) }}</span>
        </div>
        <div class="progress-row">
          <span class="progress-label">Mes</span>
          <div class="progress-bar-wrap">
            <div class="progress-bar">
              <div class="progress-fill confirmed" :style="{ width: progressPct(monthOdooHours, monthTarget) + '%' }"></div>
            </div>
          </div>
          <span class="progress-value">{{ formatHours(monthOdooHours) }}</span>
          <span class="progress-target">/ {{ formatHours(monthTarget) }}</span>
        </div>
        <div v-if="todayUnconfirmedHours > 0" class="progress-hint">
          {{ formatHours(todayUnconfirmedHours) }} sin confirmar hoy
        </div>
      </template>

      <!-- Horas dia seleccionado -->
      <template #day-hours>
        <h3 class="card-title">{{ selectedDateTitle }}</h3>
        <div class="hours-display">
          <span class="hours-value">{{ formatHours(selectedTotalHours) }}</span>
          <span class="hours-target">/ {{ formatHours(selectedTarget) }}</span>
          <span v-if="selectedUnconfirmedHours > 0" class="hours-unconfirmed">
            {{ formatHours(selectedUnconfirmedHours) }} sin confirmar
          </span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill confirmed" :style="{ width: progressPct(selectedConfirmedHours, selectedTarget) + '%' }"></div>
          <div class="progress-fill unconfirmed" :style="{ width: progressPct(selectedUnconfirmedHours, selectedTarget) + '%' }"></div>
        </div>
        <div v-if="selectedOdooHours > 0" class="hours-detail">
          <span>Odoo: {{ formatHours(selectedOdooHours) }}</span>
          <span>Captura: {{ formatHours(blocksStore.totalHoursToday) }}</span>
        </div>
      </template>

      <!-- Servicios -->
      <template #services>
        <h3 class="card-title">Servicios</h3>
        <div class="daemon-info">
          <div class="info-row">
            <span class="label">Captura</span>
            <span class="value" :class="daemonStore.captureConnected ? 'connected' : 'disconnected'">
              {{ daemonStore.captureConnected ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">Servidor</span>
            <span class="value" :class="daemonStore.statusClass">
              {{ daemonStore.connected ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">Bloques hoy</span>
            <span class="value">{{ blocksStore.blocks.length }}</span>
          </div>
        </div>
      </template>

      <!-- Top Issues -->
      <template #issues>
        <h3 class="card-title">Top Issues por Score</h3>
        <div class="top-issues">
          <div v-for="issue in issuesStore.scoredIssues.slice(0, 5)" :key="issue.id" class="issue-row">
            <span class="issue-score">{{ issue.score }}</span>
            <span class="issue-project">{{ issue.project_path }}</span>
            <span class="issue-title">{{ issue.title }}</span>
          </div>
          <EmptyState v-if="issuesStore.scoredIssues.length === 0" text="Sin issues cargadas" />
        </div>
      </template>
    </DashboardGrid>
  </div>
</template>

<style scoped>
/* Edit bar */
.edit-toggle {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.btn-edit-start {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-edit-start:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.edit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(203, 27, 33, 0.08);
  border: 1px solid var(--accent);
  border-radius: 8px;
  margin-bottom: 12px;
}

.edit-hint {
  font-size: 12px;
  color: var(--text-secondary);
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.btn-edit {
  padding: 5px 14px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn-edit.save {
  background: var(--accent);
  color: white;
}

.btn-edit.save:hover {
  background: var(--accent-hover);
}

.btn-edit.reset {
  background: none;
  color: var(--warning);
  border: 1px solid var(--warning);
}

.btn-edit.reset:hover {
  background: rgba(220, 220, 170, 0.1);
}

.btn-edit.cancel {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-edit.cancel:hover {
  background: var(--bg-hover);
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Jornada */
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

/* Progreso */
.progress-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.progress-label { min-width: 60px; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.progress-bar-wrap { flex: 1; }
.progress-bar { height: 8px; background: var(--bg-card); border-radius: 4px; overflow: hidden; display: flex; }
.progress-fill { height: 100%; transition: width 0.3s ease; }
.progress-fill.confirmed { background: var(--accent); border-radius: 4px 0 0 4px; }
.progress-fill.unconfirmed { background: var(--accent); opacity: 0.3; }
.progress-value { font-size: 14px; font-weight: 600; color: var(--text-primary); min-width: 50px; text-align: right; }
.progress-target { font-size: 12px; color: var(--text-secondary); min-width: 55px; }
.progress-hint { font-size: 11px; color: var(--text-secondary); opacity: 0.7; margin-top: -4px; padding-left: 70px; }

/* Horas dia */
.hours-display { display: flex; align-items: baseline; gap: 4px; margin-bottom: 8px; }
.hours-value { font-size: 32px; font-weight: 700; color: var(--accent); }
.hours-target { font-size: 16px; color: var(--text-secondary); }
.hours-unconfirmed { font-size: 13px; color: var(--text-secondary); opacity: 0.6; margin-left: auto; }
.hours-detail { display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--text-secondary); }

/* Servicios */
.daemon-info { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 13px; }
.info-row .label { color: var(--text-secondary); }
.info-row .value.connected { color: var(--success); }
.info-row .value.disconnected { color: var(--error); }

/* Issues */
.top-issues { display: flex; flex-direction: column; gap: 6px; }
.issue-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px; font-size: 13px; }
.issue-row:hover { background: var(--bg-hover); }
.issue-score { min-width: 32px; text-align: right; font-weight: 600; color: var(--accent); }
.issue-project { color: var(--text-secondary); font-size: 12px; min-width: 150px; }
.issue-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
