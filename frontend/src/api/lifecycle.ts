import { useQuery } from "@tanstack/react-query";
import { ApiError } from "./errors";

export type LifecycleStageContract = {
  key: string;
  label: string;
  lane: string;
  entry_requirements: string[];
  exit_requirements: string[];
  actors: string[];
  transitions: string[];
  timestamp_source: string;
};

export type LifecycleContract = {
  version: string;
  stages: LifecycleStageContract[];
};

export async function fetchLifecycleContract(signal?: AbortSignal): Promise<LifecycleContract> {
  const response = await fetch("/api/v1/lifecycle", { signal });
  if (!response.ok) {
    throw new ApiError(`Lifecycle contract request failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as LifecycleContract;
}

export function useLifecycleContract() {
  return useQuery({
    queryKey: ["lifecycle-contract"],
    queryFn: ({ signal }) => fetchLifecycleContract(signal),
    staleTime: 300_000,
  });
}
