import { computed } from 'vue';
import { useConfigStore } from '../stores/config';

const DAY_NAMES = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo'];

/**
 * Devuelve el objetivo de horas para un día dado (YYYY-MM-DD).
 * Usa weekly_hour_targets[0..6] donde 0=lunes, 6=domingo.
 */
export function getTargetForDate(date: string): number {
  const config = useConfigStore();
  const targets = config.config.weekly_hour_targets;
  if (!targets || targets.length !== 7) return config.config.daily_hour_target || 8;
  const d = new Date(date + 'T00:00:00');
  // JS: 0=domingo, queremos 0=lunes
  const dow = (d.getDay() + 6) % 7;
  return targets[dow];
}

/**
 * Objetivo semanal: suma de los 7 días.
 */
export function useWeeklyTarget() {
  const config = useConfigStore();
  return computed(() => {
    const targets = config.config.weekly_hour_targets;
    if (!targets || targets.length !== 7) return (config.config.daily_hour_target || 8) * 5;
    return targets.reduce((sum, h) => sum + h, 0);
  });
}

/**
 * Objetivo mensual: suma de targets por cada día del mes.
 */
export function getMonthlyTarget(year: number, month: number): number {
  const config = useConfigStore();
  const targets = config.config.weekly_hour_targets;
  if (!targets || targets.length !== 7) return (config.config.daily_hour_target || 8) * 22;

  let total = 0;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(year, month, d);
    const dow = (date.getDay() + 6) % 7;
    total += targets[dow];
  }
  return total;
}

/**
 * Fechas de la semana (lunes a domingo) que contiene una fecha dada.
 */
export function getWeekDates(dateStr: string): string[] {
  const d = new Date(dateStr + 'T00:00:00');
  const dow = (d.getDay() + 6) % 7; // 0=lunes
  const monday = new Date(d);
  monday.setDate(d.getDate() - dow);

  const dates: string[] = [];
  for (let i = 0; i < 7; i++) {
    const day = new Date(monday);
    day.setDate(monday.getDate() + i);
    dates.push(day.toISOString().slice(0, 10));
  }
  return dates;
}

export { DAY_NAMES };
