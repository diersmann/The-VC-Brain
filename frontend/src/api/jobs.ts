import { useQuery } from "@tanstack/react-query";
import { ApiError } from "./errors";

/** Durable job states written by the worker ledger. Unknown values are kept
 * representable so the UI does not claim a state the API did not return. */
export type JobRunStatus = "queued" | "running" | "succeeded" | "failed" | "degraded" | "cancelled" | string;

export type JobRun = {
  id: string;
  job_type: string;
  status: JobRunStatus;
  phase: string;
  attempt: number;
  progress: number;
  last_error: string | null;
  result: Record<string, unknown> | null;
  cancel_requested: boolean;
  updated_at: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export function isTerminalJobStatus(status: JobRunStatus | undefined): boolean {
  return status === "succeeded" || status === "failed" || status === "degraded" || status === "cancelled";
}

export async function fetchJobStatus(jobId: string, signal?: AbortSignal): Promise<JobRun> {
  const response = await fetch(`/api/v1/collection/jobs/${encodeURIComponent(jobId)}`, { signal });
  if (!response.ok) throw new ApiError(`Job status request failed with status ${response.status}`, response.status);
  return (await response.json()) as JobRun;
}

/** Poll a durable job until a terminal state; no polling occurs before an id
 * is returned or after the ledger reports completion/failure. */
export function useJobRun(jobId?: string) {
  return useQuery({
    queryKey: ["job-run", jobId],
    queryFn: ({ signal }) => fetchJobStatus(jobId!, signal),
    enabled: Boolean(jobId),
    staleTime: 0,
    refetchInterval: (query) => (!query.state.data || query.state.error || isTerminalJobStatus(query.state.data.status) ? false : 2_000),
  });
}
