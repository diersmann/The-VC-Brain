import { throwIfNotOk } from "./errors";

export interface Health {
  status: "ok";
  service: string;
}

export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch("/api/v1/health", { signal });

  throwIfNotOk(response, "Health request");

  return (await response.json()) as Health;
}
