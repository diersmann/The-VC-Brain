import { describe, expect, test } from "vitest";
import type { Candidate } from "../types/candidate";
import { decisionReadiness, median, ratioPercent, scorePercent } from "./portfolioMetrics";

function candidate(thesis: number | null, evidence: number | null): Candidate {
  return {
    id: "candidate-1",
    stable_id: "candidate-1",
    display_name: "Test Founder",
    email: null,
    handles: null,
    consent_state: "unknown",
    origin: "outbound",
    scores: { novelty: null, momentum: null, thesis_fit: thesis, evidence_confidence: evidence },
    latest_score_at: null,
    created_at: null,
  };
}

describe("portfolio metrics", () => {
  test("normalizes percentages and portfolio ratios", () => {
    expect(scorePercent(.76)).toBe(76);
    expect(scorePercent(76)).toBe(76);
    expect(scorePercent(null)).toBeNull();
    expect(ratioPercent(3, 8)).toBe(38);
    expect(median([80, 40, 60, null])).toBe(60);
  });

  test("partitions candidates into actionable decision states", () => {
    expect(decisionReadiness(candidate(.82, .71))).toBe("ready");
    expect(decisionReadiness(candidate(.58, .55))).toBe("investigate");
    expect(decisionReadiness(candidate(.82, null))).toBe("evidence-gap");
    expect(decisionReadiness(candidate(null, null))).toBe("evidence-gap");
  });
});
