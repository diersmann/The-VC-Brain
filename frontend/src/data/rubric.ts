/** Shared display thresholds mirrored from the versioned backend rubric. */
export const DECISION_RUBRIC = {
  version: "decision-readiness-v1",
  thesisAlignment: 75,
  evidenceConfidence: 60,
} as const;

export function rubricPercent(key: "thesisAlignment" | "evidenceConfidence"): number {
  return DECISION_RUBRIC[key];
}
