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
  <h3 class="card-title">Progreso</h3>
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
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
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
</style>
