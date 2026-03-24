<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { formatDate } from '../../composables/useFormatting';

const props = defineProps<{
  modelValue: string; // YYYY-MM-DD
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const open = ref(false);
const el = ref<HTMLElement | null>(null);

// Estado del calendario visible
const viewYear = ref(0);
const viewMonth = ref(0); // 0-11

onMounted(() => {
  const d = props.modelValue ? new Date(props.modelValue + 'T00:00:00') : new Date();
  viewYear.value = d.getFullYear();
  viewMonth.value = d.getMonth();
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

const displayValue = computed(() => {
  if (!props.modelValue) return '';
  return formatDate(props.modelValue);
});

const monthLabel = computed(() => {
  const d = new Date(viewYear.value, viewMonth.value, 1);
  const name = d.toLocaleDateString('es-ES', { month: 'long' });
  return name.charAt(0).toUpperCase() + name.slice(1);
});

const weekDays = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];

const calendarDays = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value, 1);
  const lastDay = new Date(viewYear.value, viewMonth.value + 1, 0).getDate();

  // Dia de la semana del primer dia (lunes=0)
  let startDow = first.getDay() - 1;
  if (startDow < 0) startDow = 6;

  const days: { date: string; day: number; current: boolean; today: boolean }[] = [];

  // Dias del mes anterior para rellenar
  const prevLastDay = new Date(viewYear.value, viewMonth.value, 0).getDate();
  for (let i = startDow - 1; i >= 0; i--) {
    const d = prevLastDay - i;
    const m = viewMonth.value === 0 ? 12 : viewMonth.value;
    const y = viewMonth.value === 0 ? viewYear.value - 1 : viewYear.value;
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    days.push({ date: dateStr, day: d, current: false, today: false });
  }

  // Dias del mes actual
  const todayStr = new Date().toISOString().slice(0, 10);
  for (let d = 1; d <= lastDay; d++) {
    const dateStr = `${viewYear.value}-${String(viewMonth.value + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    days.push({ date: dateStr, day: d, current: true, today: dateStr === todayStr });
  }

  // Dias del mes siguiente para completar la grilla (siempre 42 celdas = 6 filas)
  const remaining = 42 - days.length;
  for (let d = 1; d <= remaining; d++) {
    const m = viewMonth.value === 11 ? 1 : viewMonth.value + 2;
    const y = viewMonth.value === 11 ? viewYear.value + 1 : viewYear.value;
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    days.push({ date: dateStr, day: d, current: false, today: false });
  }

  return days;
});

function toggle() {
  open.value = !open.value;
  if (open.value && props.modelValue) {
    const d = new Date(props.modelValue + 'T00:00:00');
    viewYear.value = d.getFullYear();
    viewMonth.value = d.getMonth();
  }
}

function selectDay(dateStr: string) {
  emit('update:modelValue', dateStr);
  open.value = false;
}

function prevMonth() {
  if (viewMonth.value === 0) {
    viewMonth.value = 11;
    viewYear.value--;
  } else {
    viewMonth.value--;
  }
}

function nextMonth() {
  if (viewMonth.value === 11) {
    viewMonth.value = 0;
    viewYear.value++;
  } else {
    viewMonth.value++;
  }
}

function goToday() {
  const now = new Date();
  viewYear.value = now.getFullYear();
  viewMonth.value = now.getMonth();
  selectDay(now.toISOString().slice(0, 10));
}

function handleClickOutside(e: MouseEvent) {
  if (el.value && !el.value.contains(e.target as Node)) {
    open.value = false;
  }
}
</script>

<template>
  <div class="date-picker" ref="el" :class="{ open }">
    <button type="button" class="picker-trigger" @click="toggle">
      <span class="picker-icon">&#x1F4C5;</span>
      <span class="picker-value">{{ displayValue || 'Seleccionar fecha' }}</span>
      <span class="picker-arrow">{{ open ? '&#x25B2;' : '&#x25BC;' }}</span>
    </button>

    <Transition name="dropdown">
      <div v-if="open" class="picker-dropdown">
        <div class="picker-header">
          <button type="button" class="nav-btn" @click="prevMonth">&lt;</button>
          <span class="month-label">{{ monthLabel }} {{ viewYear }}</span>
          <button type="button" class="nav-btn" @click="nextMonth">&gt;</button>
        </div>

        <div class="weekdays">
          <span v-for="d in weekDays" :key="d" class="weekday">{{ d }}</span>
        </div>

        <div class="days-grid">
          <button
            v-for="(day, i) in calendarDays"
            :key="i"
            type="button"
            class="day-cell"
            :class="{
              'other-month': !day.current,
              'today': day.today,
              'selected': day.date === modelValue,
            }"
            @click="selectDay(day.date)"
          >
            {{ day.day }}
          </button>
        </div>

        <div class="picker-footer">
          <button type="button" class="today-btn" @click="goToday">Hoy</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.date-picker {
  position: relative;
}

.picker-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 5px 10px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s;
  white-space: nowrap;
}

.picker-trigger:hover {
  border-color: var(--accent);
}

.date-picker.open .picker-trigger {
  border-color: var(--accent);
  border-radius: 4px 4px 0 0;
}

.picker-icon {
  font-size: 14px;
}

.picker-value {
  flex: 1;
}

.picker-arrow {
  font-size: 8px;
  color: var(--text-secondary);
}

.picker-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: var(--z-dropdown);
  width: 260px;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-top: none;
  border-radius: 0 0 6px 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  padding: 8px;
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 8px;
}

.month-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.nav-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.nav-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  margin-bottom: 4px;
}

.weekday {
  text-align: center;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  padding: 2px 0;
}

.days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.day-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.1s;
}

.day-cell:hover {
  background: var(--bg-hover);
}

.day-cell.other-month {
  color: var(--text-secondary);
  opacity: 0.4;
}

.day-cell.today {
  border: 1px solid var(--accent);
  font-weight: 600;
}

.day-cell.selected {
  background: var(--accent);
  color: white;
  font-weight: 600;
}

.day-cell.selected:hover {
  background: var(--accent-hover);
}

.picker-footer {
  display: flex;
  justify-content: center;
  padding-top: 6px;
  border-top: 1px solid var(--border);
  margin-top: 6px;
}

.today-btn {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
}

.today-btn:hover {
  background: var(--bg-hover);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
