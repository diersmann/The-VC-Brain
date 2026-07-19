import { afterEach, expect, test, vi } from "vitest";

import { draftCandidateOutreach, fetchCandidates, recordCandidateDecision } from "./candidates";

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

  await expect(recordCandidateDecision("candidate-1", "hold", "Verify retention")).resolves.toEqual(responseBody);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/candidates/candidate-1/decision",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ action: "hold", reason: "Verify retention" }) }),
  );
});
