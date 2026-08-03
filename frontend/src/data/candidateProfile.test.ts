import { describe, expect, it } from "vitest";

import { buildFounderProfile, formatDate } from "./candidateProfile";
import type { CandidateDetail } from "../types/candidate";

describe("buildFounderProfile", () => {
  it("does not throw or invent a date for malformed timestamps", () => {
    expect(formatDate("not-a-date")).toBe("Unknown date");
    expect(formatDate(null)).toBe("Unknown date");
  });

  it("keeps unassessed axes unknown instead of turning them into zero scores", () => {
    const candidate: CandidateDetail = {
      id: "candidate-1",
      stable_id: "founder-1",
      display_name: "Ada Founder",
      email: null,
      handles: null,
      consent_state: "pending",
      origin: "outbound",
      scores: null,
      latest_score_at: null,
      created_at: null,
      opportunity: null,
      observations: [],
      claims: [],
      assessments: [],
      score_history: [],
      relationships: [],
    };

    const profile = buildFounderProfile(candidate);

    expect(profile.assessments.map((assessment) => assessment.score)).toEqual([null, null, null]);
    expect(profile.assessments.every((assessment) => assessment.rating === "Pending")).toBe(true);
    expect(profile.sourceConfidence).toBeNull();
    expect(profile.coverageScore).toBeNull();
  });

  it("keeps source confidence separate from breadth of evidence coverage", () => {
    const candidate: CandidateDetail = {
      id: "candidate-2",
      stable_id: "founder-2",
      display_name: "Grace Founder",
      email: null,
      handles: null,
      consent_state: "pending",
      origin: "outbound",
      scores: null,
      latest_score_at: null,
      created_at: null,
      opportunity: null,
      observations: [
        { id: "observation-bio", predicate: "bio", object_value: "Builder", confidence: 0.9, observed_at: "2026-01-01T00:00:00Z", source_type: "github", source_uri: "https://github.com/grace" },
        { id: "observation-revenue", predicate: "revenue", object_value: "$1m", confidence: 0.3, observed_at: "2026-01-02T00:00:00Z", source_type: "web", source_uri: "https://example.com" },
      ],
      claims: [],
      assessments: [],
      score_history: [],
      relationships: [],
    };

    const profile = buildFounderProfile(candidate);

    expect(profile.sourceConfidence).toBe(60);
    expect(profile.coverageScore).toBe(18);
    expect(profile.sourceConfidence).not.toBe(profile.coverageScore);
  });
});
