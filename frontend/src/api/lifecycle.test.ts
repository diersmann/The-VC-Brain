import { afterEach, expect, test, vi } from "vitest";

import { fetchLifecycleContract } from "./lifecycle";

afterEach(() => {
  vi.restoreAllMocks();
});

test("fetches the versioned lifecycle contract used by the workflow diagram", async () => {
  const contract = {
    version: "unified-v2",
    stages: [{
      key: "triage",
      label: "Triage",
      lane: "inbound",
      entry_requirements: ["claims"],
      exit_requirements: ["founder score"],
      actors: ["pipeline:auto"],
      transitions: ["screening"],
      timestamp_source:
        "Opportunity.created_at for initial entry; DecisionEvent.created_at for transitions",
    }],
  };
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(contract), { status: 200 }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await expect(fetchLifecycleContract()).resolves.toEqual(contract);
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/lifecycle", { signal: undefined });
});
