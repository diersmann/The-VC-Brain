import { formatPredicate } from "./candidateProfile";
import type { CandidateDetail, CandidateSLA } from "../types/candidate";
import type { FounderProfile } from "../types/profile";

export type DecisionMeta = {
  recommendation: "Proceed" | "Hold" | "Investigate";
  deadline: string;
  slaStatus: CandidateSLA["status"];
  slaAlert: boolean;
  slaStage: string | null;
  slaOwner: string;
  ask: string;
  targetOwnership: string;
  round: string;
  valuation: string;
  lead: string;
  aiSummary: string;
  thesis: string;
  product: string;
  traction: string[];
  market: string;
  competition: string;
  strengths: string[];
  risks: string[];
  conditions: string[];
};

export function createDecisionMeta(profile: FounderProfile, candidate: CandidateDetail): DecisionMeta {
  const ratings = profile.assessments.filter((item) => item.rating !== "Pending").map((item) => item.rating);
  const recommendation: DecisionMeta["recommendation"] = ratings.includes("Bearish")
    ? "Hold"
    : ratings.length === 3 && ratings.every((rating) => rating === "Bullish")
      ? "Proceed"
      : "Investigate";
  const sourceCount = new Set(candidate.observations.map((item) => item.source_type)).size;
  const traction = profile.claims.length
    ? profile.claims.slice(0, 5).map((claim) => claim.claim)
    : ["No traction claims have been recorded in the evidence store."];
  const marketEvidence = candidate.observations.filter((item) => /(market|sector|industry|category)/i.test(item.predicate));
  const competitionEvidence = candidate.observations.filter((item) => /(compet|alternative|similar)/i.test(item.predicate));
  const risks = profile.gaps.length ? profile.gaps.slice(0, 4) : ["No formal risk assessment has been recorded."];
  const sla = candidate.sla;

  return {
    recommendation,
    deadline: formatSlaDeadline(sla),
    slaStatus: sla?.status ?? "not_started",
    slaAlert: sla?.alert ?? false,
    slaStage: sla?.stage ?? null,
    slaOwner: sla?.owner ?? "Unassigned",
    ask: "Not disclosed",
    targetOwnership: "Not set",
    round: profile.stage,
    valuation: "Not disclosed",
    lead: "Not recorded",
    aiSummary: `${candidate.display_name ?? candidate.stable_id} has ${candidate.observations.length} observations from ${sourceCount} public source${sourceCount === 1 ? "" : "s"}. ${profile.summary} ${profile.thesisFit ? `Recorded thesis fit is ${profile.thesisFit}%.` : "Thesis fit has not been scored."} ${sla?.status === "breached" ? "The persisted decision SLA is breached." : ""} Recommendation: ${recommendation.toLowerCase()} pending review of the listed evidence gaps.`,
    thesis: profile.thesisFit
      ? `The recorded thesis-fit score is ${profile.thesisFit}%. ${profile.summary}`
      : "No thesis-fit assessment has been stored for this candidate. The investment team should score the opportunity against the active thesis.",
    product: profile.summary,
    traction,
    market: marketEvidence.length
      ? marketEvidence.slice(0, 3).map((item) => `${formatPredicate(item.predicate)}: ${item.object_value}`).join(" ")
      : "No market-sizing or sector claim has been recorded in the evidence store.",
    competition: competitionEvidence.length
      ? competitionEvidence.slice(0, 3).map((item) => `${formatPredicate(item.predicate)}: ${item.object_value}`).join(" ")
      : "No competitive-landscape evidence has been recorded.",
    strengths: profile.tags.length ? profile.tags.slice(0, 4) : ["No verified strengths recorded"],
    risks,
    conditions: risks.map((gap) => `Resolve: ${gap}`),
  };
}

function formatSlaDeadline(sla: CandidateSLA | null | undefined): string {
  if (!sla || sla.status === "not_started") return "Not scheduled";
  if (sla.status === "breached") return "SLA breached";
  if (sla.status === "met") return "Met";
  if (sla.remaining_seconds == null) return "Not scheduled";
  const seconds = Math.max(0, sla.remaining_seconds);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}
