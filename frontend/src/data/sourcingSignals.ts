import type { Candidate } from "../types/candidate";

export function hasHighMultiAxisSignal(candidate: Candidate): boolean {
  const values = [
    candidate.scores?.founder ?? candidate.scores?.raw?.founder,
    candidate.scores?.market ?? candidate.scores?.raw?.market,
    candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market,
  ];
  return values.every((value) => typeof value === "number" && value >= .67);
}

/**
 * Rank without averaging independent axes: a complete profile is ordered by
 * its weakest axis, while incomplete evidence remains a separate discovery
 * queue rather than being treated as a zero-quality founder score.
 */
export function rankCandidates(candidates: Candidate[]): Candidate[] {
  return [...candidates].sort((left, right) => {
    const leftAxes = axisValues(left);
    const rightAxes = axisValues(right);
    const leftComplete = leftAxes.length === 3;
    const rightComplete = rightAxes.length === 3;
    if (leftComplete !== rightComplete) return leftComplete ? -1 : 1;
    if (leftComplete && rightComplete) {
      const floorDifference = Math.min(...rightAxes) - Math.min(...leftAxes);
      if (floorDifference !== 0) return floorDifference;
      const strongestDifference = Math.max(...rightAxes) - Math.max(...leftAxes);
      if (strongestDifference !== 0) return strongestDifference;
    } else {
      const measuredDifference = rightAxes.length - leftAxes.length;
      if (measuredDifference !== 0) return measuredDifference;
    }
    return discoverySignal(right) - discoverySignal(left) || left.id.localeCompare(right.id);
  });
}

export function rankingExplanation(candidate: Candidate): string {
  return axisValues(candidate).length === 3
    ? "Ranked by the lowest independent axis"
    : "Discovery signal · axis evidence incomplete";
}

function axisValues(candidate: Candidate): number[] {
  return [
    candidate.scores?.founder ?? candidate.scores?.raw?.founder,
    candidate.scores?.market ?? candidate.scores?.raw?.market,
    candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market,
  ].filter((value): value is number => typeof value === "number");
}

function discoverySignal(candidate: Candidate): number {
  return candidate.scores?.discovery_signal ?? candidate.scores?.raw?.composite ?? 0;
}
