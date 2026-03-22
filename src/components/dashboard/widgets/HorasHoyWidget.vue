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

const confirmedPct = computed(() => progressPct(selectedConfirmedHours.value, selectedTarget.value));
const totalPct = computed(() => progressPct(selectedTotalHours.value, selectedTarget.value));

async function fetchOdooData() {
  if (!daemonStore.connected) return;
  try {
    odooEntriesToday.value = await api.getTimesheetEntries(today, today) as TimesheetEntry[];
  } catch { /* ignore */ }
}

onMounted(() => fetchOdooData());
</script>

<template>
  <div class="widget-hours">
    <h3 class="widget-title">{{ selectedDateTitle }}</h3>
    <div class="hours-hero">
      <span class="hours-current">{{ formatHours(selectedTotalHours) }}</span>
      <span class="hours-divider">/</span>
      <span class="hours-target">{{ formatHours(selectedTarget) }}</span>
    </div>
    <div v-if="selectedUnconfirmedHours > 0" class="hours-subtitle">
      {{ formatHours(selectedUnconfirmedHours) }} sin confirmar
    </div>
    <div class="progress-track">
      <div
        class="progress-bar confirmed"
        :style="{ width: confirmedPct + '%' }"
      ></div>
      <div
        class="progress-bar unconfirmed"
        :style="{ width: (totalPct - confirmedPct) + '%' }"
      ></div>
    </div>
    <div v-if="selectedOdooHours > 0" class="hours-breakdown">
      <span class="breakdown-item">
        <span class="breakdown-dot odoo"></span>
        Odoo: {{ formatHours(selectedOdooHours) }}
      </span>
      <span class="breakdown-item">
        <span class="breakdown-dot capture"></span>
        Captura: {{ formatHours(blocksStore.totalHoursToday) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.widget-hours {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.widget-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hours-hero {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.hours-current {
  font-size: var(--text-3xl);
  font-weight: 700;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.1;
}

.hours-divider {
  font-size: var(--text-xl);
  color: var(--text-muted);
  font-weight: 300;
}

.hours-target {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  font-weight: 400;
}

.hours-subtitle {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.progress-track {
  height: 6px;
  background: var(--bg-card);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  margin-top: var(--space-1);
}

.progress-bar {
  height: 100%;
  transition: width var(--duration-slow) var(--ease-out);
}

.progress-bar.confirmed {
  background: linear-gradient(90deg, var(--accent) 0%, var(--accent-hover) 100%);
  border-radius: 3px 0 0 3px;
}

.progress-bar.unconfirmed {
  background: var(--accent);
  opacity: 0.2;
}

.hours-breakdown {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.breakdown-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.breakdown-dot.odoo {
  background: var(--accent);
}

.breakdown-dot.capture {
  background: var(--info);
}
</style>
