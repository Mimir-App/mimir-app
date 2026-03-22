<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useBlocksStore } from '../../../stores/blocks';
import { useDaemonStore } from '../../../stores/daemon';
import { formatHours } from '../../../composables/useFormatting';
import { getTargetForDate, getWeekDates, getMonthlyTarget } from '../../../composables/useTargets';
import { api } from '../../../lib/api';
import type { TimesheetEntry } from '../../../lib/types';

const props = defineProps<{ config: Record<string, any> }>();

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();

const today = new Date().toISOString().slice(0, 10);
const now = new Date();

const odooEntriesToday = ref<TimesheetEntry[]>([]);
const odooEntriesWeek = ref<TimesheetEntry[]>([]);
const odooEntriesMonth = ref<TimesheetEntry[]>([]);

const weekDates = getWeekDates(today);
const weekStart = weekDates[0];
const weekEnd = weekDates[6];
const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
const monthEnd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}`;

const todayTarget = computed(() => getTargetForDate(today));
const todayOdooHours = computed(() => odooEntriesToday.value.reduce((sum, e) => sum + e.hours, 0));
const todayTotalHours = computed(() => blocksStore.totalHoursToday + todayOdooHours.value);
const todayConfirmedHours = computed(() => blocksStore.confirmedHoursToday + todayOdooHours.value);
const todayUnconfirmedHours = computed(() => blocksStore.unconfirmedHoursToday);

const weekTarget = computed(() => weekDates.reduce((sum, d) => sum + getTargetForDate(d), 0));
const weekOdooHours = computed(() => odooEntriesWeek.value.reduce((sum, e) => sum + e.hours, 0));
const monthTarget = computed(() => getMonthlyTarget(now.getFullYear(), now.getMonth()));
const monthOdooHours = computed(() => odooEntriesMonth.value.reduce((sum, e) => sum + e.hours, 0));

const showHoy = computed(() => props.config.hoy !== false);
const showSemana = computed(() => props.config.semana !== false);
const showMes = computed(() => props.config.mes !== false);

function progressPct(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min((current / target) * 100, 100);
}

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

onMounted(() => fetchOdooData());
</script>

<template>
  <h3 class="card-title">progreso</h3>
  <div v-if="showHoy" class="progress-row">
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
  <div v-if="showSemana" class="progress-row">
    <span class="progress-label">Semana</span>
    <div class="progress-bar-wrap">
      <div class="progress-bar">
        <div class="progress-fill confirmed" :style="{ width: progressPct(weekOdooHours, weekTarget) + '%' }"></div>
      </div>
    </div>
    <span class="progress-value">{{ formatHours(weekOdooHours) }}</span>
    <span class="progress-target">/ {{ formatHours(weekTarget) }}</span>
  </div>
  <div v-if="showMes" class="progress-row">
    <span class="progress-label">Mes</span>
    <div class="progress-bar-wrap">
      <div class="progress-bar">
        <div class="progress-fill confirmed" :style="{ width: progressPct(monthOdooHours, monthTarget) + '%' }"></div>
      </div>
    </div>
    <span class="progress-value">{{ formatHours(monthOdooHours) }}</span>
    <span class="progress-target">/ {{ formatHours(monthTarget) }}</span>
  </div>
  <div v-if="showHoy && todayUnconfirmedHours > 0" class="progress-hint">
    {{ formatHours(todayUnconfirmedHours) }} sin confirmar hoy
  </div>
</template>

<style scoped>
.card-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: var(--space-3);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.progress-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.progress-label {
  min-width: 55px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
}
.progress-bar-wrap { flex: 1; }
.progress-bar {
  height: 6px;
  background: var(--bg-card);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
}
.progress-fill {
  height: 100%;
  transition: width var(--duration-slow) var(--ease-out);
}
.progress-fill.confirmed {
  background: linear-gradient(90deg, var(--accent) 0%, var(--accent-hover) 100%);
  border-radius: 3px 0 0 3px;
}
.progress-fill.unconfirmed {
  background: var(--accent);
  opacity: 0.2;
}
.progress-value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  min-width: 48px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.progress-target {
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-width: 50px;
}
.progress-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: calc(-1 * var(--space-1));
  padding-left: 68px;
}
</style>
