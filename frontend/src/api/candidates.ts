import { useQuery } from "@tanstack/react-query";
import { ApiError } from "./errors";
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

export async function fetchCandidates(signal?: AbortSignal, stage?: string): Promise<Candidate[]> {
  const params = new URLSearchParams({ limit: "200" });
  if (stage) params.set("stage", stage);
  const response = await fetch(`/api/v1/candidates?${params.toString()}`, { signal });

  if (!response.ok) {
    throw new ApiError(`Candidates request failed with status ${response.status}`, response.status);
  }

  return (await response.json()) as Candidate[];
}

export function useCandidates(stage?: string) {
  return useQuery({
    queryKey: ["candidates", stage ?? "all"],
    queryFn: ({ signal }) => fetchCandidates(signal, stage),
    staleTime: 60_000,
  });
}

export async function contactCandidate(candidateId: string): Promise<void> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/contact`, { method: "POST" });
  if (!response.ok) throw new ApiError(`Contact request failed with status ${response.status}`, response.status);
}

export async function fetchCandidate(candidateId: string, signal?: AbortSignal): Promise<CandidateDetail> {
  const response = await fetch(`/api/v1/candidates/${candidateId}`, { signal });

  if (!response.ok) {
    throw new ApiError(`Candidate request failed with status ${response.status}`, response.status);
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
  opportunityId: string,
  action: DecisionAction,
  reason: string,
): Promise<DecisionResult> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id: opportunityId, action, reason }),
  });
  if (!response.ok) {
    throw new Error(`Decision request failed with status ${response.status}`);
  }
  return (await response.json()) as DecisionResult;
}

export type MemoSection = {
  title: string;
  text: string;
  evidence_ids: string[];
};

export type CandidateMemo = {
  sections: MemoSection[];
  status: "pending" | "failed" | "degraded" | "succeeded" | "missing";
  generation_mode: string | null;
  model_version: string | null;
  created_at: string | null;
};

export async function fetchCandidateMemo(candidateId: string, opportunityId: string, signal?: AbortSignal): Promise<CandidateMemo> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/memo?opportunity_id=${encodeURIComponent(opportunityId)}`, { signal });
  if (response.status === 404) return { sections: [], status: "missing", generation_mode: null, model_version: null, created_at: null };
  if (!response.ok) throw new Error(`Memo request failed with status ${response.status}`);
  return (await response.json()) as CandidateMemo;
}

export async function generateCandidateMemo(candidateId: string, opportunityId: string): Promise<void> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/memo/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
  if (!response.ok) throw new Error(`Memo generation failed with status ${response.status}`);
}
