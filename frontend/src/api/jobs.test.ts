import { afterEach, expect, test, vi } from "vitest";
import { fetchJobStatus, isTerminalJobStatus } from "./jobs";

afterEach(() => vi.restoreAllMocks());

test("reads a durable job status", async () => {
  const payload = {
    id: "job-1",
    job_type: "research_candidate",
    status: "running",
    phase: "research",
    attempt: 1,
    progress: 0.5,
    last_error: null,
    result: null,
    cancel_requested: false,
    updated_at: null,
    started_at: null,
    finished_at: null,
  };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(fetchJobStatus("job/1")).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/collection/jobs/job%2F1", { signal: undefined });
});

test("recognizes terminal success, failure, degraded, and cancellation", () => {
  expect(isTerminalJobStatus("queued")).toBe(false);
  expect(isTerminalJobStatus("running")).toBe(false);
  expect(isTerminalJobStatus("succeeded")).toBe(true);
  expect(isTerminalJobStatus("failed")).toBe(true);
  expect(isTerminalJobStatus("degraded")).toBe(true);
  expect(isTerminalJobStatus("cancelled")).toBe(true);
});
