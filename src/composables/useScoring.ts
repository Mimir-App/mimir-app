import { computed, type Ref } from 'vue';
import type { GitLabIssue, GitLabMergeRequest } from '../lib/types';
import { computeIssueScore, computeMRScore, sortByScore } from '../lib/scoring';

/**
 * Composable reactivo para scoring de issues.
 */
export function useIssueScoring(issues: Ref<GitLabIssue[]>) {
  return computed(() => {
    const scored = issues.value.map(issue => ({
      ...issue,
      score: computeIssueScore(issue),
    }));
    return sortByScore(scored);
  });
}

/**
 * Composable reactivo para scoring de MRs.
 */
export function useMRScoring(mrs: Ref<GitLabMergeRequest[]>) {
  return computed(() => {
    const scored = mrs.value.map(mr => ({
      ...mr,
      score: computeMRScore(mr),
    }));
    return sortByScore(scored);
  });
}
