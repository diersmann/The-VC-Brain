import { describe, expect, test } from "vitest";

import { hasHighMultiAxisSignal } from "../../data/sourcingSignals";
import type { Candidate } from "../../types/candidate";

function candidateWithAxes(founder: number | null, market: number | null, ideaMarket: number | null): Candidate {
  return {
    id: "candidate-1",
    stable_id: "candidate-1",
    display_name: "Test Founder",
    email: null,
    handles: null,
    consent_state: "unknown",
    origin: "outbound",
    scores: {
      novelty: null,
      momentum: null,
      thesis_fit: null,
      evidence_confidence: null,
      founder,
      market,
      idea_market: ideaMarket,
    },
    latest_score_at: null,
    created_at: null,
  };
}

describe("hasHighMultiAxisSignal", () => {
  test("requires every independent axis to reach the threshold", () => {
    expect(hasHighMultiAxisSignal(candidateWithAxes(.81, .72, .67))).toBe(true);
    expect(hasHighMultiAxisSignal(candidateWithAxes(.95, .95, .4))).toBe(false);
    expect(hasHighMultiAxisSignal(candidateWithAxes(.8, null, .8))).toBe(false);
  });
});
