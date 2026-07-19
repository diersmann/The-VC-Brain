import { useQuery } from "@tanstack/react-query";
import type { Candidate, CandidateDetail } from "../types/candidate";

export type OutreachEmailType = "founder_intro" | "request_deck" | "diligence" | "follow_up";
export type DecisionAction = "proceed" | "hold" | "decline";

export type OutreachDraft = {
  subject: string;
  body: string;
  recipient_email: string | null;
  generation_mode: "agent" | "template" | "template_fallback";
  model: string | null;
  warning: string | null;
};

export type DecisionResult = {
  event_id: string;
  prior_state: string;
  new_state: string;
  action: DecisionAction;
  reason: string;
  created_at: string;
};

export async function fetchCandidates(signal?: AbortSignal): Promise<Candidate[]> {
  const response = await fetch("/api/v1/candidates?limit=200", { signal });

  if (!response.ok) {
    throw new Error(`Candidates request failed with status ${response.status}`);
  }

  return (await response.json()) as Candidate[];
}

export function useCandidates() {
  return useQuery({
    queryKey: ["candidates"],
    queryFn: ({ signal }) => fetchCandidates(signal),
    staleTime: 60_000,
  });
}

export async function fetchCandidate(candidateId: string, signal?: AbortSignal): Promise<CandidateDetail> {
  const response = await fetch(`/api/v1/candidates/${candidateId}`, { signal });

  if (!response.ok) {
    throw new Error(`Candidate request failed with status ${response.status}`);
  }

  return (await response.json()) as CandidateDetail;
}

export function useCandidate(candidateId?: string) {
  return useQuery({
    queryKey: ["candidate", candidateId],
    queryFn: ({ signal }) => fetchCandidate(candidateId!, signal),
    enabled: Boolean(candidateId),
    staleTime: 30_000,
  });
}

export async function triggerDiscovery(query: string, source = "hackernews"): Promise<void> {
  const response = await fetch("/api/v1/collection/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, source }),
  });
  if (!response.ok) {
    throw new Error(`Discovery request failed with status ${response.status}`);
  }
}

export async function researchCandidate(candidateId: string): Promise<void> {
  const response = await fetch(`/api/v1/collection/research/${candidateId}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Research request failed with status ${response.status}`);
  }
}

export async function draftCandidateOutreach(
  candidateId: string,
  emailType: OutreachEmailType,
  brief: string,
): Promise<OutreachDraft> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/outreach-draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email_type: emailType, brief }),
  });
  if (!response.ok) {
    throw new Error(`Outreach draft request failed with status ${response.status}`);
  }
  return (await response.json()) as OutreachDraft;
}

export async function recordCandidateDecision(
  candidateId: string,
  action: DecisionAction,
  reason: string,
): Promise<DecisionResult> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, reason }),
  });
  if (!response.ok) {
    throw new Error(`Decision request failed with status ${response.status}`);
  }
  return (await response.json()) as DecisionResult;
}
