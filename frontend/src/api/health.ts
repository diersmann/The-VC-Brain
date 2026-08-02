import { ApiError } from "./errors";

export interface Health {
  status: "ok";
  service: string;
}

export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch("/api/v1/health", { signal });

  if (!response.ok) {
    throw new ApiError(`Health request failed with status ${response.status}`, response.status);
  }

  return (await response.json()) as Health;
}
