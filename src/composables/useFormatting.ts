import { useConfigStore } from '../stores/config';

/**
 * Formatea horas segun la preferencia del usuario.
 * - decimal: 1.5h
 * - hm: 1:30
 * - minutes: 90m
 */
export function formatHours(value: number): string {
  const config = useConfigStore();
  const fmt = config.config.hour_format || 'hm';

  if (fmt === 'decimal') {
    return `${value.toFixed(1)}h`;
  }

  if (fmt === 'minutes') {
    return `${Math.round(value * 60)}m`;
  }

  // hm — formato H:MM
  const h = Math.floor(value);
  const m = Math.round((value - h) * 60);
  return `${h}:${m.toString().padStart(2, '0')}`;
}

/**
 * Formatea una fecha segun la preferencia del usuario.
 * - iso: 2026-03-14
 * - eu: 14/03/2026
 * - short: 14 mar 2026
 * - long: viernes, 14 de marzo de 2026
 */
export function formatDate(dateStr: string): string {
  const config = useConfigStore();
  const fmt = config.config.date_format || 'eu';

  if (fmt === 'iso') {
    return dateStr.slice(0, 10);
  }

  const d = new Date(dateStr + (dateStr.includes('T') ? '' : 'T00:00:00'));

  if (fmt === 'eu') {
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  }

  if (fmt === 'short') {
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  // long
  return d.toLocaleDateString('es-ES', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
}

/**
 * Formatea una hora (HH:MM) desde un string ISO datetime.
 * Usa la timezone configurada por el usuario (por defecto la del sistema).
 */
export function formatTime(dateStr: string): string {
  const config = useConfigStore();
  const tz = config.config.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
  const d = new Date(dateStr);
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', timeZone: tz });
}
