<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { GitLabMergeRequest, GitLabNote, GitLabLabel, MRConflict } from '../../lib/types';
import { api } from '../../lib/api';
import { useConfigStore } from '../../stores/config';
import { formatDate } from '../../composables/useFormatting';
import ModalDialog from '../shared/ModalDialog.vue';
import ScoreBadge from '../shared/ScoreBadge.vue';

const props = defineProps<{
  mr: GitLabMergeRequest | null;
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
const conflicts = ref<MRConflict[]>([]);
const loadingConflicts = ref(false);

// Manual score inline editing
const editingScore = ref(false);
const editScoreValue = ref(0);
const scoreInput = ref<HTMLInputElement | null>(null);

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

/** Carga notas de la MR */
async function loadNotes(mr: GitLabMergeRequest) {
  loadingNotes.value = true;
  try {
    const perPage = configStore.config.issue_notes_count || 5;
    const projectId = encodeURIComponent(mr.project_path);
    notes.value = await api.getMRNotes(projectId, mr.iid, perPage);
  } catch {
    notes.value = [];
  } finally {
    loadingNotes.value = false;
  }
}

/** Carga archivos en conflicto */
async function loadConflicts(mr: GitLabMergeRequest) {
  if (!mr.has_conflicts) {
    conflicts.value = [];
    return;
  }
  loadingConflicts.value = true;
  try {
    const projectId = encodeURIComponent(mr.project_path);
    conflicts.value = await api.getMRConflicts(projectId, mr.iid);
  } catch {
    conflicts.value = [];
  } finally {
    loadingConflicts.value = false;
  }
}

/** Inicia edicion inline del manual score */
function startEditScore() {
  if (!props.mr) return;
  editScoreValue.value = props.mr.manual_priority ?? 0;
  editingScore.value = true;
  nextTick(() => {
    scoreInput.value?.focus();
    scoreInput.value?.select();
  });
}

/** Guarda el manual score */
async function saveManualScore() {
  if (!props.mr) return;
  editingScore.value = false;
  const val = Math.max(0, Math.min(200, editScoreValue.value));
  try {
    await api.updateItemPreferences('mr', props.mr.id, { manual_score: val });
    // Actualizar localmente
    props.mr.manual_priority = val;
  } catch {
    // Silenciar error
  }
}

/** Cancela la edicion */
function cancelEditScore() {
  editingScore.value = false;
}

/** Devuelve clase CSS segun el estado del pipeline */
function pipelineClass(status: string | null): string {
  if (!status) return '';
  switch (status) {
    case 'success': return 'pipeline-success';
    case 'failed': return 'pipeline-failed';
    case 'running': return 'pipeline-running';
    case 'pending':
    case 'created':
    case 'manual':
      return 'pipeline-pending';
    default: return '';
  }
}

// Watch: cuando cambia la MR, cargar datos
watch(
  () => props.mr,
  (newMR) => {
    notes.value = [];
    conflicts.value = [];
    editingScore.value = false;
    if (newMR) {
      loadNotes(newMR);
      loadConflicts(newMR);
      loadLabels();
    }
  },
);
</script>

<template>
  <ModalDialog
    :title="mr ? `${mr.project_path}#${mr.iid}` : ''"
    :open="open"
    @close="emit('close')"
  >
    <div v-if="mr" class="mr-modal-content">
      <!-- Titulo -->
      <h3 class="mr-title">{{ mr.title }}</h3>

      <!-- Labels como chips coloreados -->
      <div v-if="mr.labels.length" class="labels-row">
        <span
          v-for="l in mr.labels"
          :key="l"
          class="label-chip"
          :style="{
            backgroundColor: labelColorMap[l] ? labelColorMap[l] + '33' : 'var(--bg-card)',
            color: labelColorMap[l] || 'var(--text-primary)',
            borderColor: labelColorMap[l] || 'var(--border)',
          }"
        >{{ l }}</span>
      </div>

      <!-- State badge -->
      <div class="state-badge-row">
        <span class="state-badge" :class="'state-' + mr.state">{{ mr.state }}</span>
      </div>

      <!-- Pipeline section -->
      <div class="pipeline-section">
        <span class="meta-label">Pipeline</span>
        <span v-if="mr.pipeline_status" class="pipeline-badge" :class="pipelineClass(mr.pipeline_status)">
          {{ mr.pipeline_status }}
        </span>
        <span v-else class="meta-value muted">&mdash;</span>
      </div>

      <!-- Conflicts section -->
      <div v-if="mr.has_conflicts" class="conflicts-section">
        <div class="conflicts-header">
          <span class="conflicts-icon">&#9888;</span>
          <span class="conflicts-title">Conflictos detectados</span>
        </div>
        <div v-if="loadingConflicts" class="loading-text">Cargando conflictos...</div>
        <ul v-else-if="conflicts.length" class="conflicts-list">
          <li v-for="c in conflicts" :key="c.old_path" class="conflict-file">
            {{ c.new_path !== c.old_path ? `${c.old_path} → ${c.new_path}` : c.old_path }}
          </li>
        </ul>
        <div v-else class="conflicts-fallback">No se pudieron obtener los archivos en conflicto</div>
      </div>

      <!-- Meta info -->
      <div class="meta-section">
        <div class="meta-row">
          <span class="meta-label">Asignados</span>
          <span class="meta-value">
            {{ mr.assignees.map(a => a.username).join(', ') || '\u2014' }}
          </span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Reviewers</span>
          <span class="meta-value">
            {{ mr.reviewers.map(r => r.username).join(', ') || '\u2014' }}
          </span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Rama</span>
          <span class="meta-value branch-info">{{ mr.source_branch }} → {{ mr.target_branch }}</span>
        </div>
      </div>

      <!-- Scores -->
      <div class="scores-section">
        <div class="score-row">
          <span class="meta-label">Score total</span>
          <ScoreBadge :score="mr.score" />
        </div>
        <div class="score-row">
          <span class="meta-label">Score manual</span>
          <span v-if="!editingScore" class="manual-score-display" @click="startEditScore">
            {{ mr.manual_priority ?? 0 }}
            <span class="edit-hint">editar</span>
          </span>
          <span v-else class="manual-score-edit">
            <input
              ref="scoreInput"
              v-model.number="editScoreValue"
              type="number"
              min="0"
              max="200"
              class="score-input"
              @keyup.enter="saveManualScore"
              @keyup.escape="cancelEditScore"
              @blur="saveManualScore"
            />
          </span>
        </div>
      </div>

      <!-- Descripcion en markdown -->
      <div v-if="mr.description" class="description-section">
        <h4>Descripcion</h4>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="markdown-body" v-html="renderMarkdown(mr.description)"></div>
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

      <!-- Footer -->
      <div class="modal-footer">
        <a :href="mr.web_url" target="_blank" class="gitlab-link">Ir a GitLab</a>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.mr-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mr-title {
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

/* State badge */
.state-badge-row {
  display: flex;
}

.state-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.state-opened {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
  border: 1px solid var(--success);
}

.state-merged {
  background: rgba(203, 27, 33, 0.15);
  color: var(--accent);
  border: 1px solid var(--accent);
}

.state-closed {
  background: rgba(162, 176, 180, 0.15);
  color: var(--text-secondary);
  border: 1px solid var(--text-secondary);
}

/* Pipeline */
.pipeline-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.pipeline-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.pipeline-success {
  background: rgba(78, 201, 176, 0.15);
  color: var(--success);
  border: 1px solid var(--success);
}

.pipeline-failed {
  background: rgba(241, 76, 76, 0.15);
  color: var(--error);
  border: 1px solid var(--error);
}

.pipeline-running {
  background: rgba(220, 220, 170, 0.15);
  color: var(--warning);
  border: 1px solid var(--warning);
}

.pipeline-pending {
  background: rgba(162, 176, 180, 0.15);
  color: var(--text-secondary);
  border: 1px solid var(--text-secondary);
}

/* Conflicts */
.conflicts-section {
  border: 1px solid var(--error);
  border-radius: 8px;
  padding: 12px;
  background: rgba(241, 76, 76, 0.08);
}

.conflicts-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.conflicts-icon {
  color: var(--error);
  font-size: 16px;
}

.conflicts-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--error);
}

.conflicts-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conflict-file {
  font-size: 12px;
  font-family: monospace;
  color: var(--text-primary);
  padding: 2px 6px;
  background: rgba(241, 76, 76, 0.05);
  border-radius: 4px;
}

.conflicts-fallback {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
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

.branch-info {
  font-family: monospace;
  font-size: 12px;
}

.muted {
  color: var(--text-secondary);
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

.loading-text {
  color: var(--text-secondary);
  font-style: italic;
  font-size: 12px;
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

/* Footer */
.modal-footer {
  padding-top: 12px;
  border-top: 1px solid var(--border);
  text-align: right;
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
