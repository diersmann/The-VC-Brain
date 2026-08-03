import { useQuery } from "@tanstack/react-query";
import { ApiError } from "./errors";

export interface InvestmentThesis {
  version: string;
  name: string;
  is_active: boolean;
  stages: string[];
  sectors: string[];
  excluded_sectors: string[];
  regions: string[];
  check_size_min_k_eur: number | null;
  check_size_max_k_eur: number | null;
  ownership_target_pct: number | null;
  risk_appetite: "conservative" | "balanced" | "bold";
  scoring_weights: Record<string, number>;
  discovery_queries: string[];
  source_freshness_days: Record<string, number>;
  rubric_version: string;
  rubric_thresholds: Record<string, number>;
}

export interface ThesisPayload {
  name: string;
  stages: string[];
  sectors: string[];
  excluded_sectors: string[];
  regions: string[];
  check_size_min_k_eur: number | null;
  check_size_max_k_eur: number | null;
  ownership_target_pct: number;
  risk_appetite: "conservative" | "balanced" | "bold";
  scoring_weights: Record<string, number>;
  discovery_queries?: string[];
  source_freshness_days?: Record<string, number>;
}

export interface ThesisSaveResult {
  thesis: InvestmentThesis;
  scored_candidates: number;
}

export async function fetchActiveThesis(signal?: AbortSignal): Promise<InvestmentThesis | null> {
  const response = await fetch("/api/v1/theses/active", { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new ApiError(`Thesis request failed with status ${response.status}`, response.status);
  return (await response.json()) as InvestmentThesis;
}

export function useActiveThesis() {
  return useQuery({
    queryKey: ["active-thesis"],
    queryFn: ({ signal }) => fetchActiveThesis(signal),
    staleTime: 60_000,
  });
}

export async function saveActiveThesis(payload: ThesisPayload): Promise<ThesisSaveResult> {
  const response = await fetch("/api/v1/theses/active", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Saving thesis failed with status ${response.status}`);
  return (await response.json()) as ThesisSaveResult;
}
