<script setup lang="ts">
import { ref } from 'vue';
import type { ReviewResult } from '../../lib/types';
import { formatHours } from '../../composables/useFormatting';
import {
  XCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-vue-next';

defineProps<{
  result: ReviewResult;
}>();

const emit = defineEmits<{
  dismiss: [];
}>();

const collapsed = ref(false);

function severityIcon(severity: string) {
  switch (severity) {
    case 'error': return XCircle;
    case 'warning': return AlertTriangle;
    default: return Info;
  }
}

function severityClass(severity: string) {
  switch (severity) {
    case 'error': return 'severity-error';
    case 'warning': return 'severity-warning';
    default: return 'severity-info';
  }
}
</script>

<template>
  <div class="review-panel" role="region" aria-label="Resultado de la revision">
    <!-- Header -->
    <div class="review-header">
      <button class="btn-toggle" @click="collapsed = !collapsed" :aria-expanded="!collapsed" aria-label="Colapsar o expandir detalles">
        <ChevronDown v-if="!collapsed" :size="14" />
        <ChevronRight v-else :size="14" />
        <CheckCircle2 v-if="result.summary.errors === 0" :size="16" class="title-icon ok" />
        <AlertTriangle v-else :size="16" class="title-icon error" />
        <span>Resultado de la revision</span>
      </button>
      <button class="btn-dismiss" @click="emit('dismiss')" aria-label="Cerrar panel de revision">
        <X :size="14" />
      </button>
    </div>

    <!-- Summary (siempre visible) -->
    <div class="review-summary">
      <div class="summary-stat">
        <span class="stat-value">{{ result.summary.total_blocks }}</span>
        <span class="stat-label">bloques</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{{ formatHours(result.summary.total_hours) }}</span>
        <span class="stat-label">horas</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{{ result.summary.coverage_percent.toFixed(0) }}%</span>
        <span class="stat-label">cobertura</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{{ (result.summary.avg_confidence * 100).toFixed(0) }}%</span>
        <span class="stat-label">confianza</span>
      </div>
      <div class="summary-stat" v-if="result.summary.errors > 0">
        <span class="stat-value severity-error">{{ result.summary.errors }}</span>
        <span class="stat-label">errores</span>
      </div>
      <div class="summary-stat" v-if="result.summary.warnings > 0">
        <span class="stat-value severity-warning">{{ result.summary.warnings }}</span>
        <span class="stat-label">avisos</span>
      </div>
      <div class="summary-stat" v-if="result.summary.info > 0">
        <span class="stat-value severity-info">{{ result.summary.info }}</span>
        <span class="stat-label">info</span>
      </div>
    </div>

    <!-- Issues (colapsable) -->
    <template v-if="!collapsed">
      <div v-if="result.issues.length > 0" class="review-issues">
        <div
          v-for="(issue, idx) in result.issues"
          :key="idx"
          class="issue-row"
          :class="severityClass(issue.severity)"
        >
          <component :is="severityIcon(issue.severity)" :size="14" class="issue-icon" />
          <div class="issue-content">
            <span class="issue-block" v-if="issue.block_index >= 0">
              Bloque {{ issue.block_index + 1 }}
            </span>
            <span class="issue-message">{{ issue.message }}</span>
            <span class="issue-suggestion" v-if="issue.suggestion">{{ issue.suggestion }}</span>
          </div>
        </div>
      </div>

      <div v-else class="review-ok">
        <CheckCircle2 :size="18" />
        <span>No se encontraron problemas</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.review-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-4);
}

.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.review-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.btn-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border: none;
  background: transparent;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  cursor: pointer;
  padding: 0;
}
.btn-toggle:hover { color: var(--text-muted); }

.title-icon.ok { color: var(--success); }
.title-icon.error { color: var(--error); }

.btn-dismiss {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.btn-dismiss:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* Summary */
.review-summary {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Issues */
.review-issues {
  display: flex;
  flex-direction: column;
}

.issue-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border);
}
.issue-row:last-child { border-bottom: none; }

.issue-icon { flex-shrink: 0; margin-top: 2px; }

.issue-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.issue-block {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
}

.issue-message {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.issue-suggestion {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-style: italic;
}

/* Severity colors */
.severity-error { color: var(--error); }
.severity-warning { color: var(--warning); }
.severity-info { color: var(--text-muted); }

.issue-row.severity-error .issue-icon { color: var(--error); }
.issue-row.severity-warning .issue-icon { color: var(--warning); }
.issue-row.severity-info .issue-icon { color: var(--text-muted); }

/* OK state */
.review-ok {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-4);
  color: var(--success);
  font-size: var(--text-sm);
}
</style>
