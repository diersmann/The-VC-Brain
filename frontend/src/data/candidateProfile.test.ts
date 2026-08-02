import { describe, expect, it } from "vitest";

import { buildFounderProfile } from "./candidateProfile";
import type { CandidateDetail } from "../types/candidate";

describe("buildFounderProfile", () => {
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
  });
});
