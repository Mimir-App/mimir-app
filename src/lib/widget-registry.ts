/**
 * Registro de widgets del dashboard.
 * Define los tipos disponibles, sus metadatos y valores por defecto.
 */

export interface WidgetDef {
  type: string;
  name: string;
  description: string;
  icon: string;
  defaultSpan: [number, number]; // [rows, cols]
  configurable: boolean;
  comingSoon?: boolean;
}

export interface DashboardWidget {
  id: string;
  type: string;
  position: number;
  span: [number, number]; // [rows, cols]
  config: Record<string, any>;
}

const registry = new Map<string, WidgetDef>();

export function registerWidget(def: WidgetDef): void {
  registry.set(def.type, def);
}

export function getWidgetDef(type: string): WidgetDef | undefined {
  return registry.get(type);
}

export function getAllWidgetDefs(): WidgetDef[] {
  return Array.from(registry.values());
}

export function createWidget(type: string, position: number, configOverrides?: Record<string, any>): DashboardWidget {
  const def = registry.get(type);
  const span = def?.defaultSpan ?? [1, 1];
  return {
    id: `${type}-${Date.now()}`,
    type,
    position,
    span: [...span] as [number, number],
    config: { ...(configOverrides ?? {}) },
  };
}

export function getDefaultWidgets(): DashboardWidget[] {
  return [
    { id: 'jornada-default', type: 'jornada', position: 0, span: [1, 1], config: {} },
    { id: 'progreso-default', type: 'progreso', position: 1, span: [1, 2], config: { hoy: true, semana: true, mes: true } },
    { id: 'horas_hoy-default', type: 'horas_hoy', position: 2, span: [1, 2], config: { target: 8 } },
    { id: 'servicios-default', type: 'servicios', position: 3, span: [1, 1], config: {} },
    { id: 'top_issues-default', type: 'top_issues', position: 4, span: [1, 3], config: { count: 5 } },
  ];
}

// Registro de definiciones por defecto
registerWidget({
  type: 'jornada',
  name: 'Jornada',
  description: 'Fichaje de entrada y salida con Odoo',
  icon: '\u{1F552}',
  defaultSpan: [1, 1],
  configurable: false,
});

registerWidget({
  type: 'servicios',
  name: 'Servicios',
  description: 'Estado de los servicios (captura y servidor)',
  icon: '\u{1F4E1}',
  defaultSpan: [1, 1],
  configurable: false,
});

registerWidget({
  type: 'horas_hoy',
  name: 'Horas Hoy',
  description: 'Horas trabajadas hoy con barra de progreso',
  icon: '\u{23F1}',
  defaultSpan: [1, 2],
  configurable: true,
});

registerWidget({
  type: 'progreso',
  name: 'Progreso',
  description: 'Barras de progreso de hoy, semana y mes',
  icon: '\u{1F4CA}',
  defaultSpan: [1, 2],
  configurable: true,
});

registerWidget({
  type: 'top_issues',
  name: 'Top Issues',
  description: 'Issues con mayor puntuacion de GitLab',
  icon: '\u{1F41B}',
  defaultSpan: [1, 3],
  configurable: true,
});

registerWidget({
  type: 'mrs_pendientes',
  name: 'MRs Pendientes',
  description: 'Merge requests pendientes de revision',
  icon: '\u{1F500}',
  defaultSpan: [1, 3],
  configurable: true,
});

registerWidget({
  type: 'todos',
  name: 'Todos',
  description: 'Tareas pendientes de GitLab (TODOs)',
  icon: '\u{2705}',
  defaultSpan: [1, 2],
  configurable: true,
});

registerWidget({
  type: 'calendario',
  name: 'Calendario',
  description: 'Eventos de Google Calendar',
  icon: '\u{1F4C5}',
  defaultSpan: [1, 2],
  configurable: false,
  comingSoon: true,
});

registerWidget({
  type: 'horas_semana',
  name: 'Horas Semana',
  description: 'Resumen de horas de la semana',
  icon: '\u{1F4C8}',
  defaultSpan: [1, 2],
  configurable: false,
  comingSoon: true,
});

registerWidget({
  type: 'issues_proyecto',
  name: 'Issues por Proyecto',
  description: 'Issues agrupadas por repositorio',
  icon: '\u{1F4CC}',
  defaultSpan: [1, 2],
  configurable: true,
  comingSoon: true,
});
