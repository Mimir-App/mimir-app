<script setup lang="ts">
import { ref, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { GitLabIssue, GitLabNote, GitLabLabel, TimesheetEntry } from '../../lib/types';
import { api } from '../../lib/api';
import { useConfigStore } from '../../stores/config';
import { formatDate, formatHours } from '../../composables/useFormatting';
import ModalDialog from '../shared/ModalDialog.vue';
import ScoreBadge from '../shared/ScoreBadge.vue';

const props = defineProps<{
  issue: GitLabIssue | null;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const configStore = useConfigStore();

// Estado reactivo
const notes = ref<GitLabNote[]>([]);
const loadingNotes = ref(false);
const labels = ref<GitLabLabel[]>([]);
const timeSpentHours = ref(0);
const loadingTime = ref(false);


/** Mapa de labels -> color para chips coloreados */
const labelColorMap = ref<Record<string, string>>({});

/** Renderiza markdown de forma segura */
function renderMarkdown(md: string): string {
  const raw = marked.parse(md, { async: false }) as string;
  return DOMPurify.sanitize(raw);
}

/** Carga labels del proyecto para obtener colores */
async function loadLabels() {
  try {
    labels.value = await api.getGitlabLabels();
    const map: Record<string, string> = {};
    for (const l of labels.value) {
      map[l.name] = l.color;
    }
    labelColorMap.value = map;
  } catch {
    // Labels sin color si falla
  }
}

/** Carga notas de la issue */
async function loadNotes(issue: GitLabIssue) {
  loadingNotes.value = true;
  try {
    const perPage = configStore.config.issue_notes_count || 5;
    if (issue._source === 'github') {
      // GitHub: project_path es "owner/repo"
      const [owner, repo] = issue.project_path.split('/');
      notes.value = await api.getGithubIssueComments(owner, repo, issue.iid, perPage);
    } else {
      const projectId = encodeURIComponent(issue.project_path);
      notes.value = await api.getIssueNotes(projectId, issue.iid, perPage);
    }
  } catch {
    notes.value = [];
  } finally {
    loadingNotes.value = false;
  }
}

/** Carga horas imputadas en Odoo para la tarea vinculada */
async function loadTimeSpent(issue: GitLabIssue) {
  // Solo buscar si es GitLab (puede tener vinculo con Odoo)
  if (issue._source === 'github') {
    timeSpentHours.value = -1; // -1 = no vinculado
    return;
  }
  loadingTime.value = true;
  try {
    const now = new Date();
    const yearAgo = new Date(now);
    yearAgo.setFullYear(yearAgo.getFullYear() - 1);
    const dateFrom = yearAgo.toISOString().slice(0, 10);
    const dateTo = now.toISOString().slice(0, 10);

    const entries = await api.getTimesheetEntries(dateFrom, dateTo) as TimesheetEntry[];

    const pattern = `#${issue.iid}`;
    const matching = entries.filter(e =>
      e.description?.includes(pattern) ||
      e.description?.includes(issue.title)
    );
    timeSpentHours.value = matching.reduce((sum, e) => sum + e.hours, 0);
  } catch {
    timeSpentHours.value = 0;
  } finally {
    loadingTime.value = false;
  }
}

/** Guarda el manual score desde ScoreBadge editable */
async function saveManualScoreValue(val: number) {
  if (!props.issue) return;
  const clamped = Math.max(0, Math.min(200, val));
  try {
    await api.updateItemPreferences('issue', props.issue.id, { manual_score: clamped });
    props.issue.manual_priority = clamped;
  } catch {
    // Silenciar error
  }
}

// Watch: cuando cambia la issue, cargar datos
watch(
  () => props.issue,
  (newIssue) => {
    notes.value = [];
    timeSpentHours.value = 0;
    if (newIssue) {
      loadNotes(newIssue);
      loadTimeSpent(newIssue);
      loadLabels();
    }
  },
);
</script>

<template>
  <ModalDialog
    :title="issue ? `${issue.project_path}#${issue.iid}` : ''"
    :open="open"
    @close="emit('close')"
  >
    <div v-if="issue" class="issue-modal-content">
      <!-- Titulo -->
      <h3 class="issue-title">{{ issue.title }}</h3>

      <!-- Labels como chips coloreados -->
      <div v-if="issue.labels.length" class="labels-row">
        <span
          v-for="l in issue.labels"
          :key="l"
          class="label-chip"
          :style="{
            backgroundColor: labelColorMap[l] ? labelColorMap[l] + '33' : 'var(--bg-card)',
            color: labelColorMap[l] || 'var(--text-primary)',
            borderColor: labelColorMap[l] || 'var(--border)',
          }"
        >{{ l }}</span>
      </div>

      <!-- Meta info -->
      <div class="meta-section">
        <div v-if="issue.milestone" class="meta-row">
          <span class="meta-label">Milestone</span>
          <span class="meta-value">{{ issue.milestone }}</span>
        </div>
        <div v-if="issue.due_date" class="meta-row">
          <span class="meta-label">Fecha limite</span>
          <span class="meta-value">{{ formatDate(issue.due_date) }}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Asignados</span>
          <span class="meta-value">
            {{ issue.assignees.map(a => a.username).join(', ') || '\u2014' }}
          </span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Estado</span>
          <span class="meta-value">{{ issue.state }}</span>
        </div>
      </div>

      <!-- Scores -->
      <div class="scores-section">
        <div class="score-row">
          <span class="meta-label">Score total</span>
          <ScoreBadge :score="issue.score" />
        </div>
        <div class="score-row">
          <span class="meta-label">Score manual</span>
          <ScoreBadge
            :score="issue.manual_priority ?? 0"
            :manual-score="issue.manual_priority ?? 0"
            editable
            @update:manual-score="saveManualScoreValue"
          />
        </div>
      </div>

      <!-- Tiempo imputado -->
      <div v-if="timeSpentHours !== -1" class="time-section">
        <span class="meta-label">Tiempo imputado (Odoo)</span>
        <span v-if="loadingTime" class="meta-value loading-text">Cargando...</span>
        <span v-else class="meta-value">{{ formatHours(timeSpentHours) }}</span>
      </div>

      <!-- Descripcion en markdown -->
      <div v-if="issue.description" class="description-section">
        <h4>Descripcion</h4>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="markdown-body" v-html="renderMarkdown(issue.description)"></div>
      </div>

      <!-- Comentarios -->
      <div class="notes-section">
        <h4>Comentarios recientes</h4>
        <div v-if="loadingNotes" class="loading-text">Cargando comentarios...</div>
        <div v-else-if="notes.length === 0" class="empty-text">Sin comentarios</div>
        <div v-else class="notes-list">
          <div v-for="note in notes" :key="note.id" class="note-item">
            <div class="note-header">
              <span class="note-author">@{{ note.author.username }}</span>
              <span class="note-date">{{ formatDate(note.created_at) }}</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="note-body markdown-body" v-html="renderMarkdown(note.body)"></div>
          </div>
        </div>
      </div>

    </div>
    <template #footer>
      <a v-if="issue" :href="issue.web_url" target="_blank" class="gitlab-link">Ir a {{ issue._source === 'github' ? 'GitHub' : 'GitLab' }}</a>
    </template>
  </ModalDialog>
</template>

<style scoped>
.issue-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.issue-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  line-height: 1.4;
}

/* Labels */
.labels-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.label-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid;
}

/* Meta */
.meta-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.meta-label {
  color: var(--text-secondary);
  font-size: 13px;
}

.meta-value {
  font-size: 13px;
}

/* Scores */
.scores-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.score-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.manual-score-display {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}

.manual-score-display:hover {
  background: var(--bg-card);
}

.edit-hint {
  font-size: 10px;
  color: var(--text-secondary);
  opacity: 0;
  transition: opacity 0.15s;
}

.manual-score-display:hover .edit-hint {
  opacity: 1;
}

.score-input {
  width: 60px;
  padding: 2px 6px;
  font-size: 13px;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: 4px;
  color: var(--text-primary);
  outline: none;
  text-align: right;
}

/* Tiempo */
.time-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.loading-text {
  color: var(--text-secondary);
  font-style: italic;
  font-size: 12px;
}

/* Descripcion */
.description-section h4,
.notes-section h4 {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 8px;
  font-weight: 600;
}

.markdown-body {
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
  overflow-wrap: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  font-size: 14px;
  margin: 8px 0 4px;
}

.markdown-body :deep(p) {
  margin: 4px 0;
}

.markdown-body :deep(code) {
  background: var(--bg-card);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.markdown-body :deep(pre) {
  background: var(--bg-card);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(a) {
  color: var(--accent);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--border);
  padding-left: 10px;
  margin: 4px 0;
  color: var(--text-secondary);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 4px;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 4px 8px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--bg-card);
}

/* Notas */
.notes-section {
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.empty-text {
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.note-item {
  padding: 10px;
  background: var(--bg-card);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.note-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.note-author {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}

.note-date {
  font-size: 11px;
  color: var(--text-secondary);
}

.note-body {
  font-size: 12px;
}


.gitlab-link {
  display: inline-block;
  padding: 6px 14px;
  background: var(--accent);
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s;
}

.gitlab-link:hover {
  background: var(--accent-hover);
}
</style>
