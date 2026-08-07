import { afterEach, expect, test, vi } from "vitest";

import {
  draftCandidateOutreach,
  fetchCandidateMemo,
  fetchCandidateListPage,
  fetchCandidates,
  generateCandidateMemo,
  researchCandidate,
  recordCandidateDecision,
  triggerDiscovery,
} from "./candidates";

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

test("sends stage and origin filters to the API", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await fetchCandidates(undefined, "memo_ready", "inbound");

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/candidates?limit=200&version=v1&stage=memo_ready&origin=inbound",
    { signal: undefined, headers: { Accept: "application/vnd.the-vc-brain.candidates.v1+json" } },
  );
});

test("returns the v1 page envelope and preserves its cursor", async () => {
  const first = {
    version: "v1",
    items: [{ id: "first" }],
    next_cursor: "cursor-2",
    total_count: 2,
    limit: 1,
    search: null,
    filters: {},
  };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(first), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(fetchCandidateListPage({ cursor: "cursor-1" })).resolves.toEqual(first);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(String(fetchMock.mock.calls[0][0])).toContain("cursor=cursor-1");
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

test("returns an empty memo when no memo has been generated", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(fetchCandidateMemo("candidate-1", "opportunity-1")).resolves.toEqual({
    sections: [],
    status: "missing",
    generation_mode: null,
    model_version: null,
    created_at: null,
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/candidates/candidate-1/memo?opportunity_id=opportunity-1",
    { signal: undefined },
  );
});

test("requests an agent-authored outreach draft", async () => {
  const responseBody = {
    subject: "Exploring Aperture AI",
    body: "Hi Alice,",
    recipient_email: "alice@example.com",
    generation_mode: "agent",
    model: "gpt-4o",
    warning: null,
  };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(draftCandidateOutreach("candidate-1", "request_deck", "Ask about traction")).resolves.toEqual(responseBody);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/candidates/candidate-1/outreach-draft",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ email_type: "request_deck", brief: "Ask about traction" }) }),
  );
});

test("persists a human decision", async () => {
  const responseBody = {
    event_id: "event-1",
    prior_state: "memo_ready",
    new_state: "hold",
    action: "hold",
    reason: "Verify retention",
    created_at: "2026-07-19T10:00:00Z",
  };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(recordCandidateDecision("candidate-1", "opportunity-1", "hold", "Verify retention")).resolves.toEqual(responseBody);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/candidates/candidate-1/decision",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ opportunity_id: "opportunity-1", action: "hold", reason: "Verify retention" }) }),
  );
});

test("returns durable ids from queued collection actions", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ job_id: "discover-job", message: "queued" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ queued: 1, candidate_ids: ["candidate-1"], job_ids: ["research-job"], message: "queued" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ job_id: "memo-job", message: "queued" }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(triggerDiscovery("Berlin founders", "github")).resolves.toEqual({ job_id: "discover-job", message: "queued" });
  await expect(researchCandidate("candidate-1")).resolves.toMatchObject({ job_ids: ["research-job"] });
  await expect(generateCandidateMemo("candidate-1", "opportunity-1")).resolves.toEqual({ job_id: "memo-job", message: "queued" });
});
