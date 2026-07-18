import { useQuery } from "@tanstack/react-query";
import type { Candidate } from "../types/candidate";

export async function fetchCandidates(signal?: AbortSignal): Promise<Candidate[]> {
  const response = await fetch("/api/v1/candidates", { signal });

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
