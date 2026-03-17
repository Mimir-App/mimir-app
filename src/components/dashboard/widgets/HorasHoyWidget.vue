<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useBlocksStore } from '../../../stores/blocks';
import { useDaemonStore } from '../../../stores/daemon';
import { formatHours, formatDate } from '../../../composables/useFormatting';
import { getTargetForDate } from '../../../composables/useTargets';
import { api } from '../../../lib/api';
import type { TimesheetEntry } from '../../../lib/types';

defineProps<{ config: Record<string, any> }>();

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();
const today = new Date().toISOString().slice(0, 10);

const odooEntriesToday = ref<TimesheetEntry[]>([]);

const selectedDate = computed(() => blocksStore.selectedDate);
const selectedIsToday = computed(() => selectedDate.value === today);
const selectedTarget = computed(() => getTargetForDate(selectedDate.value));
const selectedOdooHours = computed(() => selectedIsToday.value ? odooEntriesToday.value.reduce((sum, e) => sum + e.hours, 0) : 0);
const selectedTotalHours = computed(() => blocksStore.totalHoursToday + selectedOdooHours.value);
const selectedConfirmedHours = computed(() => blocksStore.confirmedHoursToday + selectedOdooHours.value);
const selectedUnconfirmedHours = computed(() => blocksStore.unconfirmedHoursToday);
const selectedDateTitle = computed(() => selectedIsToday.value ? 'Horas Hoy' : `Horas ${formatDate(selectedDate.value)}`);

function progressPct(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min((current / target) * 100, 100);
}

async function fetchOdooData() {
  if (!daemonStore.connected) return;
  try {
    odooEntriesToday.value = await api.getTimesheetEntries(today, today) as TimesheetEntry[];
  } catch { /* ignore */ }
}

onMounted(() => fetchOdooData());
</script>

<template>
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

<style scoped>
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.hours-display { display: flex; align-items: baseline; gap: 4px; margin-bottom: 8px; }
.hours-value { font-size: 32px; font-weight: 700; color: var(--accent); }
.hours-target { font-size: 16px; color: var(--text-secondary); }
.hours-unconfirmed { font-size: 13px; color: var(--text-secondary); opacity: 0.6; margin-left: auto; }
.hours-detail { display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--text-secondary); }
.progress-bar { height: 8px; background: var(--bg-card); border-radius: 4px; overflow: hidden; display: flex; }
.progress-fill { height: 100%; transition: width 0.3s ease; }
.progress-fill.confirmed { background: var(--accent); border-radius: 4px 0 0 4px; }
.progress-fill.unconfirmed { background: var(--accent); opacity: 0.3; }
</style>
