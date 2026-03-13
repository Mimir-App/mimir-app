<script setup lang="ts">
import { onMounted, computed } from 'vue';
import { useBlocksStore } from '../stores/blocks';
import { useDaemonStore } from '../stores/daemon';
import { useIssuesStore } from '../stores/issues';

const blocksStore = useBlocksStore();
const daemonStore = useDaemonStore();
const issuesStore = useIssuesStore();

const hoursProgress = computed(() => {
  const target = 8;
  const current = blocksStore.totalHoursToday;
  return Math.min((current / target) * 100, 100);
});

onMounted(() => {
  daemonStore.fetchStatus();
  blocksStore.fetchBlocks();
  issuesStore.fetchIssues();
});
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-grid">
      <!-- Estado del daemon -->
      <div class="card">
        <h3 class="card-title">Estado del Daemon</h3>
        <div class="daemon-info">
          <div class="info-row">
            <span class="label">Estado</span>
            <span class="value" :class="daemonStore.statusClass">
              {{ daemonStore.connected ? 'Conectado' : 'Desconectado' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">Modo</span>
            <span class="value">{{ daemonStore.modeLabel }}</span>
          </div>
          <div class="info-row">
            <span class="label">Último poll</span>
            <span class="value">{{ daemonStore.status.last_poll ?? '—' }}</span>
          </div>
        </div>
      </div>

      <!-- Horas del día -->
      <div class="card">
        <h3 class="card-title">Horas Hoy</h3>
        <div class="hours-display">
          <span class="hours-value">{{ blocksStore.totalHoursToday.toFixed(1) }}</span>
          <span class="hours-target">/ 8h</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: hoursProgress + '%' }"></div>
        </div>
      </div>

      <!-- Bloques pendientes -->
      <div class="card">
        <h3 class="card-title">Bloques Pendientes</h3>
        <div class="stat-value">{{ blocksStore.pendingBlocks.length }}</div>
        <div class="stat-label">bloques sin enviar a Odoo</div>
      </div>

      <!-- Top Issues -->
      <div class="card card-wide">
        <h3 class="card-title">Top Issues por Score</h3>
        <div class="top-issues">
          <div
            v-for="issue in issuesStore.scoredIssues.slice(0, 5)"
            :key="issue.id"
            class="issue-row"
          >
            <span class="issue-score">{{ issue.score }}</span>
            <span class="issue-project">{{ issue.project_path }}</span>
            <span class="issue-title">{{ issue.title }}</span>
          </div>
          <div v-if="issuesStore.scoredIssues.length === 0" class="empty-state">
            Sin issues cargadas
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.card-wide {
  grid-column: span 3;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.daemon-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-row .label {
  color: var(--text-secondary);
}

.info-row .value.connected {
  color: var(--success);
}

.info-row .value.disconnected {
  color: var(--error);
}

.hours-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.hours-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--accent);
}

.hours-target {
  font-size: 16px;
  color: var(--text-secondary);
}

.progress-bar {
  height: 6px;
  background: var(--bg-card);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--warning);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.top-issues {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.issue-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.issue-row:hover {
  background: var(--bg-hover);
}

.issue-score {
  min-width: 32px;
  text-align: right;
  font-weight: 600;
  color: var(--accent);
}

.issue-project {
  color: var(--text-secondary);
  font-size: 12px;
  min-width: 150px;
}

.issue-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  color: var(--text-secondary);
  font-style: italic;
  padding: 8px;
}
</style>
