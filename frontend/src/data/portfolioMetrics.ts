import type { Candidate } from "../types/candidate";

export type DecisionReadiness = "ready" | "investigate" | "evidence-gap";

export function scorePercent(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  return Math.max(0, Math.min(100, Math.round(value <= 1 ? value * 100 : value)));
}

export function displayScore(value: number | null | undefined, alreadyPercent = false): string {
  if (value == null) return "Not scored";
  return `${alreadyPercent ? value : Math.round(value * 100)}%`;
}

export function candidateThesisPercent(candidate: Candidate): number | null {
  return scorePercent(candidate.scores?.thesis_fit);
}

export function candidateEvidencePercent(candidate: Candidate): number | null {
  return scorePercent(candidate.scores?.evidence_confidence);
}

export function candidateDecisionScore(candidate: Candidate): number | null {
  const values = [
    candidate.scores?.thesis_fit,
    candidate.scores?.raw?.composite,
    candidate.scores?.founder,
    candidate.scores?.market,
    candidate.scores?.idea_market,
    candidate.scores?.momentum,
  ];
  const value = values.find((item): item is number => typeof item === "number");
  return scorePercent(value);
}

export function hasDecisionScore(candidate: Candidate): boolean {
  return candidateDecisionScore(candidate) !== null;
}

export function isThesisAligned(candidate: Candidate): boolean {
  return (candidateThesisPercent(candidate) ?? -1) >= 75;
}

export function isEvidenceReady(candidate: Candidate): boolean {
  return (candidateEvidencePercent(candidate) ?? -1) >= 60;
}

export function decisionReadiness(candidate: Candidate): DecisionReadiness {
  if (isThesisAligned(candidate) && isEvidenceReady(candidate)) return "ready";
  if (hasDecisionScore(candidate) && (candidateEvidencePercent(candidate) ?? -1) >= 40) return "investigate";
  return "evidence-gap";
}

export function ratioPercent(part: number, total: number): number {
  return total > 0 ? Math.round(part / total * 100) : 0;
}

export function median(values: Array<number | null>): number {
  const available = values.filter((value): value is number => value !== null).sort((left, right) => left - right);
  if (!available.length) return 0;
  const middle = Math.floor(available.length / 2);
  return available.length % 2 === 0 ? Math.round((available[middle - 1] + available[middle]) / 2) : available[middle];
}
