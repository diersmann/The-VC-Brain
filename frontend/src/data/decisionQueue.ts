import type { Candidate } from "../types/candidate";

export type DecisionSort = "thesis" | "founder" | "market" | "idea-market" | "newest" | "name";

export function sortDecisionCandidates(candidates: Candidate[], sortBy: DecisionSort): Candidate[] {
  const sorted = [...candidates];
  if (sortBy === "name") {
    return sorted.sort((left, right) => candidateName(left).localeCompare(candidateName(right)));
  }
  if (sortBy === "newest") {
    return sorted.sort(
      (left, right) =>
        dateValue(right.created_at) - dateValue(left.created_at)
        || candidateName(left).localeCompare(candidateName(right)),
    );
  }
  const scoreFor = (candidate: Candidate): number | null => {
    if (sortBy === "thesis") return candidate.scores?.thesis_fit ?? null;
    if (sortBy === "founder") return candidate.scores?.founder ?? null;
    if (sortBy === "market") return candidate.scores?.market ?? null;
    return candidate.scores?.idea_market ?? null;
  };
  return sorted.sort(
    (left, right) =>
      compareNullableScores(scoreFor(left), scoreFor(right))
      || candidateName(left).localeCompare(candidateName(right)),
  );
}

function compareNullableScores(left: number | null, right: number | null): number {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  return right - left;
}

function candidateName(candidate: Candidate): string {
  return candidate.display_name ?? candidate.stable_id;
}

function dateValue(value: string | null): number {
  return value ? Date.parse(value) : 0;
}
