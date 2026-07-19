import type { Candidate } from "../types/candidate";
import { candidateEvidencePercent, candidateThesisPercent, decisionReadiness } from "./portfolioMetrics";

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

export function buildDecisionBrief(candidate: Candidate): string {
  const name = candidate.display_name ?? "This founder";
  const company = candidate.profile?.company ? ` at ${candidate.profile.company}` : "";
  const evidenceSummary = cleanSummary(candidate.profile?.summary);
  const thesis = candidateThesisPercent(candidate);
  const evidence = candidateEvidencePercent(candidate);
  const scoreContext = [
    thesis == null ? "thesis fit is not yet scored" : `thesis fit is ${thesis}%`,
    evidence == null ? "evidence confidence is still pending" : `evidence confidence is ${evidence}%`,
  ].join(" and ");
  const readiness = decisionReadiness(candidate);
  const decisionContext = readiness === "ready"
    ? `The current record shows ${scoreContext}, making the opportunity ready for investor review.`
    : readiness === "investigate"
      ? `The current record shows ${scoreContext}; targeted diligence is still needed before a decision.`
      : `The current record shows ${scoreContext}; more decision-critical evidence is required.`;

  if (evidenceSummary) return `${evidenceSummary} ${decisionContext}`;
  return `${name}${company} has a limited research summary in the database. ${decisionContext}`;
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

function cleanSummary(value: string | null | undefined): string {
  if (!value) return "";
  const normalized = value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  const shortened = normalized.length > 190 ? `${normalized.slice(0, 189).trimEnd()}…` : normalized;
  return /[.!?…]$/.test(shortened) ? shortened : `${shortened}.`;
}
