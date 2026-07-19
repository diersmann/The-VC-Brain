import { useQuery } from "@tanstack/react-query";
import type { Candidate, CandidateDetail } from "../types/candidate";

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
