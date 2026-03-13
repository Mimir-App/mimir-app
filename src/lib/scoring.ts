/**
 * Motor de scoring para issues y MRs de GitLab.
 * Portado de core/scoring.py del proyecto task-management-view.
 */

import type { GitLabIssue, GitLabMergeRequest } from './types';

/** Pesos de cada factor de scoring */
const WEIGHTS = {
  MANUAL_PRIORITY_MAX: 100,
  LABEL_PRIORITY_MAX: 100,
  STATE_MILESTONE_MAX: 50,
  COMMENTS_MAX: 30,
  DUE_DATE_MAX: 50,
  MR_CONFLICTS: 20,
  FAILED_PIPELINE: 15,
} as const;

/** Labels que incrementan prioridad */
const PRIORITY_LABELS: Record<string, number> = {
  'priority::critical': 100,
  'priority::high': 75,
  'priority::medium': 50,
  'priority::low': 25,
  'Expedite': 100,
};

function scoreLabelPriority(labels: string[]): number {
  let max = 0;
  for (const label of labels) {
    const val = PRIORITY_LABELS[label];
    if (val !== undefined && val > max) max = val;
  }
  return max;
}

function scoreStateMilestone(state: string, milestone: string | null): number {
  let score = 0;
  if (state === 'opened') score += 20;
  if (milestone) score += 30;
  return Math.min(score, WEIGHTS.STATE_MILESTONE_MAX);
}

function scoreComments(count: number): number {
  return Math.min(count * 5, WEIGHTS.COMMENTS_MAX);
}

function scoreDueDate(dueDate: string | null): number {
  if (!dueDate) return 0;
  const now = new Date();
  const due = new Date(dueDate);
  const daysUntil = (due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);

  if (daysUntil < 0) return WEIGHTS.DUE_DATE_MAX;       // Vencida
  if (daysUntil <= 1) return 40;
  if (daysUntil <= 3) return 30;
  if (daysUntil <= 7) return 20;
  if (daysUntil <= 14) return 10;
  return 0;
}

export function computeIssueScore(issue: GitLabIssue): number {
  const manual = issue.manual_priority ?? 0;
  const label = scoreLabelPriority(issue.labels);
  const state = scoreStateMilestone(issue.state, issue.milestone);
  const comments = scoreComments(issue.user_notes_count);
  const due = scoreDueDate(issue.due_date);

  return manual + label + state + comments + due;
}

export function computeMRScore(mr: GitLabMergeRequest): number {
  const manual = mr.manual_priority ?? 0;
  const label = scoreLabelPriority(mr.labels);
  const state = scoreStateMilestone(mr.state, null);
  const comments = scoreComments(mr.user_notes_count);
  const conflicts = mr.has_conflicts ? WEIGHTS.MR_CONFLICTS : 0;
  const pipeline = mr.pipeline_status === 'failed' ? WEIGHTS.FAILED_PIPELINE : 0;

  return manual + label + state + comments + conflicts + pipeline;
}

export function sortByScore<T extends { score: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => b.score - a.score);
}

export function groupByProject<T extends { project_path: string }>(
  items: T[]
): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const item of items) {
    if (!groups[item.project_path]) {
      groups[item.project_path] = [];
    }
    groups[item.project_path].push(item);
  }
  return groups;
}
