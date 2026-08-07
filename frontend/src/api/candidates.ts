import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { throwIfNotOk } from "./errors";
import type { Candidate, CandidateDetail } from "../types/candidate";

export type OutreachEmailType = "founder_intro" | "request_deck" | "diligence" | "follow_up";
export type DecisionAction = "proceed" | "hold" | "decline";
export type CandidateOrigin = "inbound" | "outbound";

export type CandidateListResponse = {
  version: "v1";
  items: Candidate[];
  next_cursor: string | null;
  total_count: number;
  limit: number;
  search: string | null;
  filters: Record<string, string>;
  /** True only when an older server returned the legacy bare array shape. */
  legacy?: boolean;
};

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

export async function fetchCandidates(
  signal?: AbortSignal,
  stage?: string,
  origin?: CandidateOrigin,
  search?: string,
): Promise<Candidate[]> {
  // Preserve the legacy array consumer contract while keeping requests
  // bounded. Consumers that need more than the first page should use the
  // versioned fetchCandidateListPage cursor contract explicitly.
  const result = await fetchCandidateListPage({ signal, stage, origin, search });
  return result.items;
}

export async function fetchCandidateListPage({
  signal,
  stage,
  origin,
  search,
  cursor,
}: {
  signal?: AbortSignal;
  stage?: string;
  origin?: CandidateOrigin;
  search?: string;
  cursor?: string;
}): Promise<CandidateListResponse> {
  const params = new URLSearchParams({ limit: "200", version: "v1" });
  if (stage) params.set("stage", stage);
  if (origin) params.set("origin", origin);
  if (search?.trim()) params.set("search", search.trim());
  if (cursor) params.set("cursor", cursor);
  const response = await fetch(`/api/v1/candidates?${params.toString()}`, {
    signal,
    headers: { Accept: "application/vnd.the-vc-brain.candidates.v1+json" },
  });

  throwIfNotOk(response, "Candidates request");

  const payload = (await response.json()) as Candidate[] | CandidateListResponse;
  if (Array.isArray(payload)) {
    return {
      version: "v1",
      items: payload,
      next_cursor: null,
      total_count: payload.length,
      limit: payload.length,
      search: search?.trim() || null,
      filters: { ...(stage ? { stage } : {}), ...(origin ? { origin } : {}) },
      legacy: true,
    };
  }
  return payload;
}

export function useCandidates(stage?: string, origin?: CandidateOrigin, search?: string) {
  return useQuery({
    queryKey: ["candidates", stage ?? "all", origin ?? "all", search?.trim() ?? ""],
    queryFn: ({ signal }) => fetchCandidates(signal, stage, origin, search),
    staleTime: 60_000,
  });
}

/**
 * Read one bounded v1 page when callers need authoritative totals/cursors.
 * `useCandidates` intentionally preserves the legacy array shape for existing
 * screens; new paginated screens should consume this hook directly.
 */
export function useCandidateList(stage?: string, origin?: CandidateOrigin, search?: string) {
  return useQuery({
    queryKey: ["candidate-list", stage ?? "all", origin ?? "all", search?.trim() ?? ""],
    queryFn: ({ signal }) => fetchCandidateListPage({ signal, stage, origin, search }),
    staleTime: 60_000,
  });
}

/**
 * Read a cursor-paginated v1 candidate list. Each page keeps the server's
 * authoritative total and next cursor so screens can explicitly consume more
 * records without silently fetching an unbounded result set.
 */
export function useInfiniteCandidateList(stage?: string, origin?: CandidateOrigin, search?: string) {
  return useInfiniteQuery({
    queryKey: ["candidate-list-pages", stage ?? "all", origin ?? "all", search?.trim() ?? ""],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ signal, pageParam }) => fetchCandidateListPage({ signal, stage, origin, search, cursor: pageParam }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 60_000,
  });
}

export async function contactCandidate(candidateId: string): Promise<void> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/contact`, { method: "POST" });
  throwIfNotOk(response, "Contact request");
}

export type CandidateFeedbackAction = "dismiss" | "save" | "defer" | "assign";

export async function recordCandidateFeedback(
  candidateId: string,
  action: CandidateFeedbackAction,
  reason: string,
): Promise<void> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, reason }),
  });
  throwIfNotOk(response, "Feedback request");
}

export async function fetchCandidate(candidateId: string, signal?: AbortSignal): Promise<CandidateDetail> {
  const response = await fetch(`/api/v1/candidates/${candidateId}`, { signal });

  throwIfNotOk(response, "Candidate request");

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

export function useCandidateMemo(candidateId?: string, opportunityId?: string) {
  return useQuery({
    queryKey: ["candidate-memo", candidateId, opportunityId],
    queryFn: ({ signal }) => fetchCandidateMemo(candidateId!, opportunityId!, signal),
    enabled: Boolean(candidateId && opportunityId),
    staleTime: 30_000,
  });
}

export type QueueJobResponse = { job_id: string | null; message: string };

export type ResearchQueueResponse = {
  queued: number;
  candidate_ids: string[];
  job_ids: string[];
  message: string;
};

export async function triggerDiscovery(query: string, source = "hackernews"): Promise<QueueJobResponse> {
  const response = await fetch("/api/v1/collection/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, source }),
  });
  throwIfNotOk(response, "Discovery request");
  return (await response.json()) as QueueJobResponse;
}

export async function researchCandidate(candidateId: string): Promise<ResearchQueueResponse> {
  const response = await fetch(`/api/v1/collection/research/${candidateId}`, { method: "POST" });
  throwIfNotOk(response, "Research request");
  return (await response.json()) as ResearchQueueResponse;
}

export type ResearchStatus = {
  candidate_id: string;
  status: "not_started" | "pending" | "completed";
  research_observations: number;
  latest_scores: Record<string, unknown> | null;
  scored_at: string | null;
};

export async function fetchResearchStatus(
  candidateId: string,
  signal?: AbortSignal,
): Promise<ResearchStatus> {
  const response = await fetch(`/api/v1/collection/research/${candidateId}/status`, { signal });
  throwIfNotOk(response, "Research status");
  return (await response.json()) as ResearchStatus;
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
  throwIfNotOk(response, "Outreach draft request");
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
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({ opportunity_id: opportunityId, action, reason }),
  });
  throwIfNotOk(response, "Decision request");
  return (await response.json()) as DecisionResult;
}

export type MemoSection = {
  title: string;
  text: string;
  claim_ids: string[];
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
  throwIfNotOk(response, "Memo request");
  return (await response.json()) as CandidateMemo;
}

export async function generateCandidateMemo(candidateId: string, opportunityId: string): Promise<QueueJobResponse> {
  const response = await fetch(`/api/v1/candidates/${candidateId}/memo/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
  throwIfNotOk(response, "Memo generation");
  return (await response.json()) as QueueJobResponse;
}
