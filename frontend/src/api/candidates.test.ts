import { afterEach, expect, test, vi } from "vitest";

import { fetchCandidates } from "./candidates";

afterEach(() => {
  vi.restoreAllMocks();
});

test("returns candidates from the API", async () => {
  const mockData = [
    {
      id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      stable_id: "founder-001",
      display_name: "Alice Chen",
      email: "alice@example.com",
      handles: { linkedin: "alice-chen" },
      consent_state: "granted",
      origin: "inbound",
      scores: { novelty: 0.85, momentum: 0.72, thesis_fit: 0.91, evidence_confidence: 0.64 },
      latest_score_at: "2026-07-17T10:00:00Z",
      created_at: "2026-06-01T08:00:00Z",
    },
  ];

  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );

  const result = await fetchCandidates();
  expect(result).toEqual(mockData);
});

test("throws on non-ok response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(null, { status: 500 }),
    ),
  );

  await expect(fetchCandidates()).rejects.toThrow("Candidates request failed with status 500");
});
